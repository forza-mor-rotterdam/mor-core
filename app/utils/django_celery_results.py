import ast
import importlib
import json


def restart_task(original_task):
    if original_task.status != "FAILURE":
        return False, f'{original_task.task_id} => Skipped. Not in "FAILURE" State'
    try:
        task_actual_name = original_task.task_name.split(".")[-1]
        module_name = ".".join(original_task.task_name.split(".")[:-1])
        kwargs = json.loads(
            original_task.task_kwargs.replace('"', "").replace("'", '"')
            if original_task.task_kwargs
            else "{}"
        )
        args = ast.literal_eval(ast.literal_eval(original_task.task_args))
        getattr(importlib.import_module(module_name), task_actual_name).apply_async(
            args=args, kwargs=kwargs, task_id=original_task.task_id
        )
        return True, f"{original_task.task_id} => Successfully sent to queue for retry."
    except Exception as ex:
        return False, f"{original_task.task_id} => Unable to process. Error: {ex}"
