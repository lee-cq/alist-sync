import time
from concurrent.futures import ThreadPoolExecutor
from copy import copy


class MyThreadPoolExecutor(ThreadPoolExecutor):
    def wait(self):
        while self._work_queue.qsize():
            time.sleep(3)

