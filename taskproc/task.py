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
from common import TaskProcError

class Task:
    """A Task is a unit of work.

    Tasks are run by calling the run() method, which by default calls
    the callable func passed to the constructor.  Tasks can require
    other tasks, by passing them in requires when constructing, or by
    using add_requirement.

    :param func: what to run for task
    :type func: function
    :param requires: tasks required before this task
    :type requires: list of Task
    :param args: additional arguments to pass to `func`
    :type args: tuple
    :param kwargs: additional keyword arguments to pass to `func`
    :type kwargs: dict
    """

    # use empty to mark empty results as None is a valid result
    class _Empty():
        pass
    empty = _Empty()

    def __init__(self, func=None, requires=[], args=(), kwargs={}):

        # keep track of tasks we require first. These are mapped to
        # indices into the return result array to preserve ordering
        self.requires = {}
        for i, req in enumerate(requires):
            if req in self.requires:
                raise TaskProcError("Duplicate requirement found")
            else:
                self.requires[req] = i

        #: `Task` objects pending on completion of this task (set)
        self.pendingon = set()

        #: results of processed required tasks (list)
        self.reqresults = [Task.empty]*len(requires)

        #: call by `run()` by default when task executed (function or callable)
        self.func = func

        #: additional arguments passed to `func` (tuple)
        self.args = args
        #: additional keyword arguments passed to `func` (dict)
        self.kwargs = kwargs

        # requirements need to know we require them
        for rq in requires:
            rq.pendingon.add(self)

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
        """Add a requirement task to this task.

        :param req: add as requirement to run before this `Task`
        :type req: Task

        Note: do not add to the requirements if this task has already
        been added to a TaskQueue, unless you know that it has other
        requirements which have not been met. The task may have
        already been queued for execution.

        Changing the requirements of a task after it has been added
        means that the TaskQueue will not detect required tasks with
        unmet dependencies at the end of run.

        """
        if req in self.requires:
            raise TaskProcError("Duplicate requirement found")

        self.requires[req] = len(self.reqresults)
        self.reqresults.append(Task.empty)
        req.pendingon.add(self)

    def run(self):
        """Called when task is run. Optionally override this.

        By default runs ``self.func(self.reqresults, *self.args, **self.kwargs)``
        """
        if self.func is not None:
            return self.func(self.reqresults, *self.args, **self.kwargs)
