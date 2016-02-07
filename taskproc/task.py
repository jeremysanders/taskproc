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
    the callable func passed to the constructor.

    Tasks can require other tasks, by passing them in requires when
    constructing, or by using add_requirement. This constructs a tree
    or graph of tasks.

    Members:
    func: function to call if set
    args: extra arguments to func
    kwargs: extra keyword arguments to func

    The following members should not be modified:

    requires: remaining list of tasks required by this task
    reqresults: filled list of results preduced by tasks that
                this task requires
    pendingon: set of tasks which require this task

    """

    # use empty to mark empty results as None is a valid result
    class _Empty():
        pass
    empty = _Empty()

    def __init__(self, func=None, requires=[], args=(), kwargs={}):
        """Construct Task

        func: optional function to call. This function receives as its
              parameter a list of the results of all of its
              requirements. Optionally arguments args and keyword
              arguments kwargs are also parameters.

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

        # these are the Tasks pending on this task
        self.pendingon = set()

        # results from our requirements
        self.reqresults = [Task.empty]*len(requires)

        # function to call
        self.func = func

        # extra arguments for function
        self.args = args
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

        By default runs self.func(reqresults, *self.args, **self.kwargs)
        """
        if self.func is not None:
            return self.func(self.reqresults, *self.args, **self.kwargs)
