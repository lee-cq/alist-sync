import time
from concurrent.futures import ThreadPoolExecutor


class MyThreadPoolExecutor(ThreadPoolExecutor):
    def work_qsize(self):
        return self._work_queue.qsize()

    def wait(self):
        while self._work_queue.qsize():
            time.sleep(3)

    def join(self):
        self.wait()
        self.shutdown()

    def submit_wait(self, __fn, *args, **kwargs):
        while self._work_queue.qsize() > 10:
            time.sleep(5)
        return self.submit(__fn, *args, **kwargs)
