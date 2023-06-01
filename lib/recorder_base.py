from abc import abstractmethod
from threading import Thread

class RecorderBase(Thread):
    @abstractmethod
    def isRecording(self) -> bool:
        pass

    @abstractmethod
    def encounteredError(self) -> bool:
        pass

    @abstractmethod
    def getStopTime(self) -> float:
        pass

    @abstractmethod
    def getFreshClone(self) -> "RecorderBase":
        pass

    @abstractmethod
    def startRecording(self, metadata: dict):
        pass

    @abstractmethod
    def stopRecording(self):
        pass

    @abstractmethod
    def finish(self):
        pass