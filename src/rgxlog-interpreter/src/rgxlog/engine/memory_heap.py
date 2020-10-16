from abc import abstractmethod


class MemoryHeap:
    def collect_garbage(self):
        self._some_func()

    def _some_func(self):
        # use aux{1,2,3} to implement generic gc logic
        pass

    # TODO obviously rename these
    @abstractmethod
    def _aux1(self):
        pass

    @abstractmethod
    def _aux2(self):
        pass

    @abstractmethod
    def _aux3(self):
        pass
