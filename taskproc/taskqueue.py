#   Copyright 2016 Jeremy Sanders

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#       http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import print_function
import threading

try:
    # python 3
    import queue
except ImportError:
    # python 2.x
    import Queue as queue

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
        """Add task to queue to be processed."""

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

        abortpending: if there are encountered tasks with unsatisfied
                      dependencies at the end, raise a TaskProcError

        """
        self._process_queue()
        if self.pending and abortpending:
            raise TaskProcError(
                "Pending tasks with unsatisfied dependencies remain in queue")

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass

class TaskQueueSingle(BaseTaskQueue):
    """Simple queue where items are processed in the main thread."""

    def _process_next(self):
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
            self._process_next()

class TaskQueueThread(BaseTaskQueue):
    """A queue of tasks to run which uses multiple threads."""

    def __init__(self, nthreads, onstart=None, onend=None):
        """Initialise task processing queue using threads.

        nthreads: number of threads
        onstart: optional function to call on thread start
        onend: optional function to call on thread end
        """

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
        """Start processing threads."""

        if self.started is not False:
            raise QueueError("start() can only be called once")

        for t in self.threads:
            t.daemon = True
            t.start()
        self.started = True

    def end(self):
        """End processing threads."""

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

                    # without lock, then pendtask could be added twice to
                    # the queue
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

###########################################################################
## Self test below

def testqueue(taskqueue):
    """Test that the queue produces the right results in the right order."""

    import hashlib

    def testfunc(res, i):
        """Return a hash of the index plus the other results."""
        m = hashlib.md5()
        m.update(str(i).encode('utf-8'))
        for r in res:
            m.update(r.encode('utf-8'))
        return m.hexdigest()

    # make a set of tasks which depend on random-like other tasks
    tasks = []
    for i in range(1000):
        requires = []
        if len(tasks)>0:
            # always depend on the first task
            requires.append(tasks[0])
            for j in range(min(20, len(tasks)-1)):
                t = tasks[(j*412591231+13131) % len(tasks)]
                if t not in requires:
                    requires.append(t)

        task = Task(func=testfunc, args=(i,), requires=requires)
        tasks.append(task)

    # this task depends on everything
    finaltask = Task(func=testfunc, args=(0,), requires=tasks)

    taskqueue.add(finaltask)
    with taskqueue:
        taskqueue.process()

    # this is a hash of all the previous results
    m = hashlib.md5()
    for v in finaltask.reqresults:
        m.update(v.encode('utf-8'))
    digest = m.hexdigest()

    if digest != 'f77e8e0478e1bc41fdfeaef65ebb3c6d':
        raise RuntimeError('Self test did not produce correct result')

def runtest():
    """Test the different kinds of queue."""
    testqueue(TaskQueueSingle())
    testqueue(TaskQueueThread(4))
    print('Test success')

if __name__ == "__main__":
    runtest()
