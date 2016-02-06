from __future__ import print_function
import threading

try:
    # python 3
    import queue
except ImportError:
    # python 2.x
    import Queue as queue

class Task:
    def __init__(self, func=None, requires=[], args=(), kwargs={}):
        """Task object.

        Tasks require other tasks (specified in requires or see
        add_requirement)

        func is an optional function to call, taking at least one
        argument, which is the list of the results of all the tasks
        which are required.

        args: arguments appended to task function call
        kwargs: keyword arguments appended to task function call.
        """

        # keep track of tasks we require first. These are mapped to
        # indices into the return result array
        self.requires = {req: i for i, req in enumerate(requires)}

        # these are the Tasks which require this task
        self.requiredfor = set()

        # results from our requirements
        self.reqresults = [None]*len(requires)

        # function to call
        self.func = func

        # extra arguments for function
        self.args = args
        self.kwargs = kwargs

        # requirements need to know we require them
        for rq in requires:
            rq.requiredfor.add(self)

    def add_requirement(self, req):
        """Add a reqirement to this task."""
        self.requires[req] = len(self.reqresults)
        self.reqresults.append(None)
        req.requiredfor.add(self)

    def run(self):
        """Caled when task is run. Optionally override this."""
        if self.func is not None:
            return self.func(self.reqresults, *self.args, **self.kwargs)

class TaskQueueError(RuntimeError):
    """Exception raised if error encountered in queuing."""
    pass

class TaskQueue:
    def __init__(self):
        # items to process
        self.queue = queue.Queue()

        # tasks we have encountered, but have not processed
        self.pending = set()

    def add_task(self, task):
        """Add task to queue to be processed."""
        if task.requires:
            raise TaskQueueError(
                "Cannot add tasks with unmet dependencies")
        self.pending.add(task)
        self.queue.put(task)

    def _process_queue(self):
        """Overridden in subclasses."""
        pass

    def process(self, abortpending=False):
        """Process all items in queue.

        abortpending: if there are encountered tasks with unsatisfied
        dependencies at the end, raise a TaskQueueError
        """
        self._process_queue()
        if self.pending and abortpending:
            raise TaskQueueError(
                "Pending tasks with unsatisfied dependencies remain in queue")

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass

class TaskQueueSingle(TaskQueue):
    """Simple queue where items are processed in this thread."""

    def _process_next(self):
        task = self.queue.get()

        # tasks with unmet dependencies should not be encountered
        assert not task.requires

        # do the work of the task
        retn = task.run()

        # remove from set of all tasks to run
        self.pending.remove(task)

        # for tasks which require this task
        for reqfor in task.requiredfor:
            # add to pending
            self.pending.add(reqfor)

            # update their results entry with our results
            residx = reqfor.requires[task]
            reqfor.reqresults[residx] = retn

            # remove ourselves from their requirements
            del reqfor.requires[task]

            # if they have empty requirements, add to tasks to run
            if not reqfor.requires:
                self.queue.put(reqfor)

        # avoid dependency loops
        task.requiredfor.clear()

        self.queue.task_done()

    def _process_queue(self):
        """Do work of processing."""
        while not self.queue.empty():
            self._process_next()

class TaskQueueThread(TaskQueue):
    def __init__(self, nthreads, onstart=None, onend=None):
        """Initialise task processing queue using threads.

        nthreads: number of threads
        onstart: optional function to call on thread start
        onend: optional function to call on thread end
        """

        TaskQueue.__init__(self)
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
            for reqfor in task.requiredfor:
                # add to pending
                self.pending.add(reqfor)

                # update their results entry with our results
                residx = reqfor.requires[task]
                reqfor.reqresults[residx] = retn

                # without lock, then reqfor could be added twice to
                # the queue
                with self.reslock:
                    # remove ourselves from their requirements
                    del reqfor.requires[task]

                    # if they have empty requirements, add to tasks to run
                    if not reqfor.requires:
                        self.queue.put(reqfor)

            # avoid dependency loops
            task.requiredfor.clear()

            # tell queue that we're done and it's safe to exit if all
            # items have been processed
            self.queue.task_done()

        if self.onend:
            self.onend()

    def _process_queue(self):
        """Wait until queue is empty."""
        self.queue.join()

import time
def ft1(x):
    print("t1", x)
    time.sleep(5)
    return 1

def ft2a(x):
    print("t2a", x)
    time.sleep(4)
    return 2
def ft2b(x):
    print("t2b", x)
    time.sleep(4)
    return 2.5

def ft3(x):
    print("t3", x)
    time.sleep(6)
    return 3
def ft4(x):
    print("t4", x)
    time.sleep(1)

    return 42

def main():
    t1 = Task(func=ft1)
    t2a = Task(func=ft2a, requires=[t1])
    t2b = Task(func=ft2b, requires=[t1])
    t3 = Task(func=ft3, requires=[t2a, t1])
    t4 = Task(func=ft4, requires=[t2b, t1])
    t3.add_requirement(t2b)
    q = TaskQueueSingle()
    #q = TaskQueueThread(1, onstart=lambda: print("start"))
    with q:
        q.add_task(t1)
        q.process(abortpending=True)

if __name__ == "__main__":
    main()
