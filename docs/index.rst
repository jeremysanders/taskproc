.. taskproc documentation master file, created by
   sphinx-quickstart on Sun Feb  7 12:02:29 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

taskproc's documentation
========================

Contents:

.. toctree::
   :maxdepth: 2

Introduction
============
taskproc (task processor) is a simple Python module designed for
running a set of tasks which can have dependencies on each other. The
idea is to have a make-like dependency resolution within a Python
program. Tasks are queued for execution until their requirements are
met. When executed, tasks can return a value which is then passed down
to dependent tasks.

There are two modes of task execution: simple execution of tasks in
the main program or multi-threaded execution.

taskproc is licensed under the Apache 2.0 license and is copyright
Jeremy Sanders. It should be compatible with Python 2.6+ and Python
3.2+.

Examples
========

Simple functions
****************

.. code:: python

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

   # single-threaded processing
   queue = taskproc.TaskQueue()
   queue.add(task3)

   # "with" statement optional for single-threaded processing but is
   # required (or start()/stop() used) for TaskQueueThreaded
   with queue:
       queue.process()

Here is a simple example executing three tasks in the main thread. The
results from `func1()` and `func2()` are passed in the list `dep_results`
to `func3()`, which are then summed.
This will print the values 12 and 42 (ordering is not guaranteed for
independent tasks), then the sum 54. Note that tasks do not
necessarily to return values and could execute external data
processing commands.

Subclassing and passing extra arguments
***************************************

.. code:: python

   from __future__ import print_function
   import time
   import taskproc

   class Task1(taskproc.Task):
       def run(self):
           print('Task 1')
           time.sleep(5)

   def taskfunc(dep_results, num):
       print('Task', num)
       time.sleep(5)

   task1 = Task1()
   task2 = taskproc.Task(func=taskfunc, args=(2,), requires=[task1])
   task3 = taskproc.Task(func=taskfunc, args=(3,), requires=[task1])
   task4 = taskproc.Task(func=taskfunc, args=(4,), requires=[task1,task2])

   queue = taskproc.TaskQueueThread(2)
   queue.add(task4)
   with queue:
       queue.process()

The following example uses subclasses `Task` instead of supplying a
function for `task1`. It uses the `args` parameter for the tasks 2-4
which supplies extra aguments to the function. The `TaskQueueThread`
uses two threads, which means `task2` and `task3` are run
simultaneously.


API documentation
=================

.. automodule:: taskproc

.. autoclass:: Task
    :members:

.. autoclass:: TaskQueue
    :members:
    :inherited-members:

.. autoclass:: TaskQueueThread
    :members:
    :inherited-members:

.. autoclass:: TaskProcError

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

