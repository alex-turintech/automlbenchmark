import sys
sys.path.append("D:\\repositories/openml-python")

import openml

if __name__ == '__main__':
    suite = openml.study.get_suite(218)
    tag = 'study_218'
    # Use local variables to avoid repeatedly accessing object attributes.
    tasks = suite.tasks
    get_task = openml.tasks.get_task
    get_dataset = openml.datasets.get_dataset
    for taskid in tasks:
        print('collecting t/', taskid)
        task = get_task(taskid, download_data=False)
        dataset_id = task.dataset_id  # avoid attribute access twice
        print('collecting d/', dataset_id)
        dataset = get_dataset(dataset_id, download_data=False)
        print('tagging')
        # dataset.push_tag(tag)