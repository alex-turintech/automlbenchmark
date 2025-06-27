from amlb.benchmark import TaskConfig
from amlb.data import Dataset
from amlb.utils import call_script_in_same_dir, unsparsify

def setup(*args, **kwargs):
    call_script_in_same_dir(__file__, "setup.sh", *args, **kwargs)

def run(dataset: Dataset, config: TaskConfig):
    from frameworks.shared.caller import run_in_venv

    # Use local variables to avoid unnecessary attribute access overhead.
    train, test, predictors = dataset.train, dataset.test, dataset.predictors
    # "Enc" attributes might be large arrays, do not duplicate them in memory structures.
    X_train, X_test = train.X_enc, test.X_enc

    # Only use unsparsify (which could be memory intensive) on targets.
    y_train, y_test = unsparsify(train.y_enc, test.y_enc)

    # Use generator expression directly to reduce intermediate list allocations.
    # Explicitly make predictors_type a tuple to reduce overhead, or a generator if supported downstream.
    # However, since we're passing to run_in_venv, that usually requires serializable types; so, keep as list.
    predictors_type = ['Numerical' if p.is_numerical() else 'Categorical' for p in predictors]

    # Direct construction to avoid temporary dictionaries.
    data = {
        'train': {
            'X': X_train,
            'y': y_train
        },
        'test': {
            'X': X_test,
            'y': y_test
        },
        'predictors_type': predictors_type
    }

    return run_in_venv(__file__, "exec.py",
                       input_data=data, dataset=dataset, config=config)