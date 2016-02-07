taskproc
========

Introduction
------------

taskproc (task processor) is a simple Python module designed for
running a set of tasks which can have dependencies on each other. The
idea is to have a make-like dependency resolution within a Python
program. Tasks are queued for execution until their requirements are
met. When executed, tasks can return a value which is then passed down
to dependent tasks.

There are two modes of task execution: simple execution of tasks in
the main program or multi-threaded execution.

taskproc is licensed under the Apache 2.0 license and is copyright
Jeremy Sanders.

Example usage
-------------

Here is a simple example executing three tasks in the main thread. The
results from `func1()` and `func2()` are passed in the list `dep_results`
to `func3()`, which are then summed.

```python
import taskproc

def func1(dep_results):
    num = 42
    print(num)
    return num

def func2(dep_results):
    num = 12
    print(num)
    return num

def func3(dep_results):
    num = sum(dep_results)
    print(num)
    return num

task1 = taskproc.Task(func=func1)
task2 = taskproc.Task(func=func2)
task3 = taskproc.Task(func=func3, requires=[task1, task2])

queue = taskproc.TaskQueueSingle()
queue.add(task3)
with queue:
    queue.process()
```

This will print the values 12 and 42 (ordering is not guaranteed for
independent tasks), then the sum 54. Note that tasks do not
necessarily to return values and could execute external data
processing commands.

