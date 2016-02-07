PyTaskProc
==========

Introduction
------------

PyTaskProc (Python Task Processor) is a simple Python module designed
for running a set of tasks which can have dependencies on each
other. The idea is to have a make-like dependency resolution within a
Python program. Tasks are queued for execution until their
requirements are met. When executed, tasks can return a value which is
then passed down to dependent tasks.

There are two modes of task execution: simple execution of tasks in
the main program or multi-threaded execution.

Example usage
-------------

> import taskproc
>
> def func1(dep_results):
>     num = 42
>     print(num)
>     return num
>
> def func2(dep_results):
>     num = dep_results[0]*2
>     print(num)
>     return num
>
> task1 = taskproc.Task(func=func1)
> task2 = taskproc.Task(func=func2, requires=[task1])
>
> queue = taskproc.TaskQueueSingle()
> queue.add(task2)
> with queue:
>     queue.process()

This will print 42 followed by 84.
