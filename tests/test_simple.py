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

# a simple test of dependencies

from __future__ import print_function
import hashlib
import sys

sys.path.append('..')
sys.path.append('.')

import taskproc

# a task class test
class TestTask(taskproc.Task):
    def __init__(self, retnval, correct, requires=[]):
        taskproc.Task.__init__(self, requires=requires)
        self.retnval = retnval
        self.correct = correct

    def run(self):
        assert self.correct == self.reqresults
        #print(self.retnval, self.correct)
        return self.retnval

# a function test
def testfunc(reqresults, retnval, correct):
    assert reqresults == correct
    #print(retnval, correct)
    return retnval

def test(taskqueue):

    t1 = TestTask(1, [])
    t2 = taskproc.Task(func=testfunc, args=(2, [1]), requires=[t1])
    t3 = taskproc.Task(func=testfunc, args=(3, [2,1]), requires=[t2, t1])
    t4 = TestTask(4, [2,3], requires=[t2, t3])
    t5 = TestTask(5, [1,2], requires=[t1, t2])

    t10 = TestTask(10, [4, 5], requires=[t4, t5])
    taskqueue.add(t10)
    with taskqueue:
        taskqueue.process()

def runtest():
    try:
        # test both standard and threaded queues
        test(taskproc.TaskQueue())
        # do this lots of times to try to check for races
        for i in range(1000):
            test(taskproc.TaskQueueThread(4))
    except Exception:
        print('%s: test failure' % sys.argv[0])
        sys.exit(1)

    print('%s: test sucess' % sys.argv[0])
    sys.exit(0)

if __name__ == "__main__":
    runtest()
