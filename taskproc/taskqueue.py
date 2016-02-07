#   Copyright 2016 Jeremy Sanders
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#############################################################################

from __future__ import print_function
import threading

try:
    # python 3
    import queue
except ImportError:
    # python 2.x
    import Queue as queue

from .common import TaskProcError

class BaseTaskQueue:
    """Base class for other task queue types."""

    def __init__(self):
        # items to process
        self.queue = queue.Queue()
        # tasks we have encountered, but have not processed
        self.pending = set()
        # lock tree when adding new entries or returning results
        self.treelock = threading.Lock()

    def add(self, task):
        """Add task to queue to be processed.

        :param task: `Task` to add, this should be the `Task` that
          depends on all other required tasks.
        """

        with self.treelock:
            # Recursively build up queue of edge nodes. Written as a loop
            # to avoid recursion limits.
            stack = [task]
            while stack:
                t = stack.pop()
                if t not in self.pending:
                    # examine tasks which haven't been encountered before
                    self.pending.add(t)
                    if t.requires:
                        # further nodes to process
                        stack += t.requires
                    else:
                        # add edge nodes to queue
                        self.queue.put(t)

    def _process_queue(self):
        """Overridden in subclasses."""
        pass

    def process(self, abortpending=True):
        """Process all items in queue.

        :param abortpending: if there are encountered tasks with unsatisfied
          dependencies at the end, raise a `TaskProcError`
        """
        self._process_queue()
        if self.pending and abortpending:
            raise TaskProcError(
                "Pending tasks with unsatisfied dependencies remain in queue")

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass

class TaskQueue(BaseTaskQueue):
    """Process Tasks in a simple linear way."""

    def process_next(self):
        task = self.queue.get()

        # tasks with unmet dependencies should not be encountered
        assert not task.requires

        # do the work of the task
        retn = task.run()

        # remove from set of all tasks to run
        self.pending.remove(task)

        # for tasks which require this task
        for pendtask in task.pendingon:
            # add to pending
            self.pending.add(pendtask)

            # update their results entry with our results
            residx = pendtask.requires[task]
            pendtask.reqresults[residx] = retn

            # remove ourselves from their requirements
            del pendtask.requires[task]

            # if they have empty requirements, add to tasks to run
            if not pendtask.requires:
                self.queue.put(pendtask)

        # avoid dependency loops
        task.pendingon.clear()

        self.queue.task_done()

    def _process_queue(self):
        """Do work of processing."""
        while not self.queue.empty():
            self.process_next()

class TaskQueueThread(BaseTaskQueue):
    """Process Tasks with multiple threads.

    :param nthreads: number of threads to use
    :type nthreads: int
    :param onstart: run this at the start of each thread
    :type onstart: callable
    :param onend: run this when finishing each thread
    :type onend: callable

    When using threads care must be taken if common objects are
    accessed in the different tasks.

    The recommended way to use this class is to wrap
    `TaskQueueThread.process()` with a `with` statement which
    automatically calls start() and stop(), e.g.

    .. code:: python

      q = TaskQueueThread(q)
      q.add(...)
      with q:
          q.process()

    """

    def __init__(self, nthreads, onstart=None, onend=None):
        BaseTaskQueue.__init__(self)
        self.onstart = onstart
        self.onend = onend

        # have threads started?
        self.started = False

        # special end value
        self.done = object()

        # create threads
        self.threads = [
            threading.Thread(target=self._run_thread) for i in range(nthreads)
            ]

    def start(self):
        """Start processing threads. This must be called before `process()` or
        a `with` statement should be used."""

        if self.started is not False:
            raise TaskProcError("start() can only be called once")

        for t in self.threads:
            t.daemon = True
            t.start()
        self.started = True

    def end(self):
        """End processing threads. This should be called before the program
        ends or a `with` statement should be used."""

        assert self.started

        # tell threads to finish
        for i in range(len(self.threads)):
            self.queue.put(self.done)

        # wait until termination
        while self.threads:
            t = self.threads.pop()
            t.join()

        self.started = None

    def __enter__(self):
        """Start processing threads."""
        self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        """End procesing threads."""
        if self.started:
            self.end()

    def _run_thread(self):
        """Repeat processing queue until None is received."""

        if self.onstart:
            self.onstart()

        while True:
            task = self.queue.get()
            # object used to mark end of processing
            if task is self.done:
                break

            # do the work of the task
            retn = task.run()

            # Below is all locked to avoid any problems if add is
            # called. Finer-grained locking appeared to be slower.
            with self.treelock:
                # remove from set of all tasks to run
                self.pending.remove(task)

                # for tasks which require this task
                for pendtask in task.pendingon:
                    # add to pending
                    self.pending.add(pendtask)

                    # update their results entry with our results
                    residx = pendtask.requires[task]
                    pendtask.reqresults[residx] = retn

                    # remove ourselves from their requirements
                    del pendtask.requires[task]

                    # if they have empty requirements, add to tasks to run
                    if not pendtask.requires:
                        self.queue.put(pendtask)

            # avoid dependency loops by removing references to other
            # tasks
            task.pendingon.clear()

            # tell queue that we're done and it's safe to exit if all
            # items have been processed
            self.queue.task_done()

        if self.onend:
            self.onend()

    def _process_queue(self):
        """Wait until queue is empty."""
        self.queue.join()
