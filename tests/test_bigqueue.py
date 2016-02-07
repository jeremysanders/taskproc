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

# this is a test where we construct a large chain of dependencies
# using 1000 Tasks and ensure we get the right answer after running
# them all

from __future__ import print_function
import hashlib
import sys

sys.path.append('..')
sys.path.append('.')

import taskproc

def testfunc(res, i):
    """Return a hash of the index plus the other results."""
    m = hashlib.md5()
    m.update(str(i).encode('utf-8'))
    for r in res:
        m.update(r.encode('utf-8'))
    return m.hexdigest()

def testqueue(taskqueue):
    """Test that the queue produces the right results in the right order."""

    # make a set of tasks which depend on random-like other tasks
    # the funny numbers are a rubbish random number generator
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

        task = taskproc.Task(func=testfunc, args=(i,), requires=requires)
        tasks.append(task)

    # this task depends on everything
    finaltask = taskproc.Task(func=testfunc, args=(0,), requires=tasks)

    # do the work
    taskqueue.add(finaltask)
    with taskqueue:
        taskqueue.process()

    # this is a hash of all the previous results
    m = hashlib.md5()
    for v in finaltask.reqresults:
        m.update(v.encode('utf-8'))
    digest = m.hexdigest()

    # this is a precomputed check
    if digest != 'f77e8e0478e1bc41fdfeaef65ebb3c6d':
        raise RuntimeError('Self test did not produce correct result')

def runtest():
    try:
        # test both standard and threaded queues
        testqueue(taskproc.TaskQueue())
        testqueue(taskproc.TaskQueueThread(4))
    except Exception:
        print('%s: test failure' % sys.argv[0])
        sys.exit(1)

    print('%s: test sucess' % sys.argv[0])
    sys.exit(0)

if __name__ == "__main__":
    runtest()
