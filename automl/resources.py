"""
**resources** modules exposes a singleton ``Resources`` instance providing easy access to app configuration properties,
as well as handy methods to access other resources like *automl frameworks* and *benchmark definitions*
"""
import copy
import logging
import os
import re
import sys

from .utils import Namespace, config_load, lazy_property, memoize, normalize_path


log = logging.getLogger(__name__)


class Resources:

    @staticmethod
    def _normalize(config: Namespace, replace=None):
        def nz_path(path):
            if replace is not None:
                path = path.format(**replace)
            return normalize_path(path)

        normalized = copy.copy(config)
        for k, v in config:
            if isinstance(v, Namespace):
                normalized[k] = Resources._normalize(v, replace=replace)
            elif re.search(r'_(dir|file|cmd)s?$', k):
                normalized[k] = [nz_path(p) for p in v] if isinstance(v, list) else nz_path(v)
        return normalized

    def __init__(self, config: Namespace):
        self.config = Resources._normalize(config, replace=dict(input=config.input_dir, output=config.output_dir, user=config.user_dir))
        self.config.predictions_dir = os.path.join(self.config.output_dir, 'predictions')
        self.config.scores_dir = os.path.join(self.config.output_dir, 'scores')
        self.config.logs_dir = os.path.join(self.config.output_dir, 'logs')
        os.makedirs(self.config.predictions_dir, exist_ok=True)
        os.makedirs(self.config.scores_dir, exist_ok=True)
        os.makedirs(self.config.logs_dir, exist_ok=True)
        log.debug("Using config:\n%s", self.config)

        # allowing to load custom modules from user and input directories
        sys.path.extend([normalize_path(config.user_dir), normalize_path(config.input_dir)])
        log.debug("Extended Python sys.path to user and input directories: %s", sys.path)

    def framework_definition(self, name):
        """
        :param name:
        :return: name of the framework as defined in the frameworks definition file
        """
        framework = self._frameworks[name.lower()]
        if not framework:
            raise ValueError("Incorrect framework `{}`: not listed in {}".format(name, self.config.frameworks.definition_file))
        return framework, framework.name

    @lazy_property
    def _frameworks(self):
        frameworks_file = self.config.frameworks.definition_file
        log.info("Loading frameworks definitions from %s.", frameworks_file)
        if not isinstance(frameworks_file, list):
            frameworks_file = [frameworks_file]

        frameworks = Namespace()
        for ff in frameworks_file:
            frameworks + config_load(ff)

        for name, framework in frameworks:
            framework.name = name
            self._validate_framework(framework)
        for name, framework in dict(frameworks).items():
            frameworks[name.lower()] = framework
        log.debug("Using framework definitions:\n%s", frameworks)
        return frameworks

    @memoize
    def benchmark_definition(self, name):
        """
        :param name: name of the benchmark as defined by resources/benchmarks/{name}.yaml or the path to a user-defined benchmark description file.
        :return:
        """
        benchmark_name = name
        benchmark_dir = self.config.benchmarks.definition_dir
        if not isinstance(benchmark_dir, list):
            benchmark_dir = [benchmark_dir]

        benchmark_file = None
        for bd in benchmark_dir:
            bf = os.path.join(bd, "{}.yaml".format(benchmark_name))
            if os.path.exists(bf):
                benchmark_file = bf
                break

        if benchmark_file is None:
            benchmark_file = name
            benchmark_name, _ = os.path.splitext(os.path.basename(name))

        if not os.path.exists(benchmark_file):
            # should we support s3 and check for s3 path before raising error?
            raise ValueError("Incorrect benchmark name or path `{}`, name not available in {}.".format(name, self.config.benchmarks.definition_dir))

        log.info("Loading benchmark definitions from %s.", benchmark_file)
        tasks = config_load(benchmark_file)
        for task in tasks:
            self._validate_task(task)
        log.debug("Using benchmark definition:\n%s", tasks)
        return tasks, benchmark_name, benchmark_file

    def _validate_framework(self, framework):
        if framework['module'] is None:
            framework.module = 'automl.frameworks.'+framework.name

        if framework['setup_args'] is None:
            framework.setup_args = None

        if framework['setup_cmd'] is None:
            framework.setup_cmd = None

        did = self.config.docker.image_defaults
        if framework['docker_image'] is None:
            framework['docker_image'] = did
        for conf in ['author', 'image', 'tag']:
            if framework.docker_image[conf] is None:
                framework.docker_image[conf] = did[conf]

    def _validate_task(self, task):
        missing = []
        for conf in ['name', 'openml_task_id', 'metric']:
            if task[conf] is None:
                missing.append(conf)
        if len(missing) > 0:
            raise ValueError("{missing} mandatory properties as missing in task definition {taskdef}".format(missing=missing, taskdef=task))

        for conf in ['max_runtime_seconds', 'cores', 'folds', 'max_mem_size_mb']:
            if task[conf] is None:
                task[conf] = self.config.benchmarks.defaults[conf]
                log.debug("Config `{config}` not set for task {name}, using default `{value}`".format(config=conf, name=task.name, value=task[conf]))

        conf = 'ec2_instance_type'
        if task[conf] is None:
            task[conf] = self.config.aws.ec2.instance_type
            log.debug("Config `{config}` not set for task {name}, using default `{value}`".format(config=conf, name=task.name, value=task[conf]))


__INSTANCE__: Resources = None


def from_config(config: Namespace):
    global __INSTANCE__
    __INSTANCE__ = Resources(config)


def from_configs(*configs: Namespace):
    global __INSTANCE__
    __INSTANCE__ = Resources(Namespace.merge(*configs, deep=True))


def get() -> Resources:
    return __INSTANCE__


def config():
    return __INSTANCE__.config

