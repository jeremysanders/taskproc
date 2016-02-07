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

class TaskProcError(RuntimeError):
    """Exception raised if error encountered in this module."""
    pass

class Task:
    """A Task is a unit of work.

    Tasks are run by calling the run() method which by default calls
    the func passed to the constructor.

    Tasks can require other tasks, by passing them in requires when
    constructing, or by using add_requirement. This constructs a tree
    or graph of tasks.

    Members:
    reqresults: list of results preduced by tasks that this task requires
    func: function to call if set
    args: extra arguments to func
    kwargs: extra keyword arguments to func
    pending: set of tasks which require this task
    """

    # use empty to mark empty results as None is a valid result
    class _Empty():
        pass
    empty = _Empty()

    def __init__(self, func=None, requires=[], args=(), kwargs={}):
        """Construct Task

        func: optional function to call, taking at least one argument
        (plus optionally given args and kwargs). The parameter is the
        list of the results of all required tasks (in order given).

        args: arguments appended to task function call
        kwargs: keyword arguments appended to task function call.

        """

        # keep track of tasks we require first. These are mapped to
        # indices into the return result array to preserve ordering
        self.requires = {}
        for i, req in enumerate(requires):
            if req in self.requires:
                raise TaskProcError("Duplicate requirement found")
            else:
                self.requires[req] = i

        # these are the Tasks which require this task
        self.pending = set()

        # results from our requirements
        self.reqresults = [Task.empty]*len(requires)

        # function to call
        self.func = func

        # extra arguments for function
        self.args = args
        self.kwargs = kwargs

        # requirements need to know we require them
        for rq in requires:
            rq.pending.add(self)

    def __repr__(self):
        """Brief description of Task."""
        parts = ['%s at 0x%x' % (self.__class__.__name__, id(self))]
        if self.func is not None:
            parts.append('func=%s' % repr(self.func))
        if self.args:
            parts.append('args=%s' % repr(self.args))
        if self.kwargs:
            parts.append('kwargs=%s' % repr(self.kwargs))

        return '<%s>' % (', '.join(parts))

    def add_requirement(self, req):
        """Add a reqirement to this task."""
        if req in self.requires:
            raise TaskProcError("Duplicate requirement found")

        self.requires[req] = len(self.reqresults)
        self.reqresults.append(Task.empty)
        req.pending.add(self)

    def run(self):
        """Caled when task is run. Optionally override this.

        By default runs self.func(reqresults, *self.args, **self.kwargs)
        """
        if self.func is not None:
            return self.func(self.reqresults, *self.args, **self.kwargs)

class BaseTaskQueue:
    """Base class for other task queue types."""

    def __init__(self):
        # items to process
        self.queue = queue.Queue()
        # tasks we have encountered, but have not processed
        self.pending = set()

    def add(self, task):
        """Add task to queue to be processed."""

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

    def process(self, abortpending=False):
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
        for pendtask in task.pending:
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
        task.pending.clear()

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

        # lock used in processing results
        self.reslock = threading.Lock()

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

            # Remove from set of all tasks to run. Should be
            # thread-safe as task won't get added again if it is
            # queued
            self.pending.remove(task)

            # for tasks which require this task
            for pendtask in task.pending:
                # add to pending
                self.pending.add(pendtask)

                # update their results entry with our results
                residx = pendtask.requires[task]
                pendtask.reqresults[residx] = retn

                # without lock, then pendtask could be added twice to
                # the queue
                with self.reslock:
                    # remove ourselves from their requirements
                    del pendtask.requires[task]

                    # if they have empty requirements, add to tasks to run
                    if not pendtask.requires:
                        self.queue.put(pendtask)

            # avoid dependency loops
            task.pending.clear()

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
    for i in xrange(1000):
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
        taskqueue.process(abortpending=True)

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
