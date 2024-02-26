from concurrent.futures import ThreadPoolExecutor
from copy import copy


class MyThreadPoolExecutor(ThreadPoolExecutor):
    def wait(self):
        while True:
            for t in copy(self._threads):
                t.join()
