from concurrent.futures import ThreadPoolExecutor
from copy import copy


class MyThreadPoolExecutor(ThreadPoolExecutor):
    def wait(self):
        # FIXBUG: 修复线程池无法等待所有线程结束的问题
        while True:
            for t in copy(self._threads):
                t.join()
