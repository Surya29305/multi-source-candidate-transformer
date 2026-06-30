from abc import ABC, abstractmethod
from models.raw import RawCandidate

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> RawCandidate:
        """
        Parses a file and extracts candidate details into a RawCandidate model.
        
        Args:
            file_path: Absolute or relative path to the input file.
            
        Returns:
            RawCandidate: The parsed candidate details.
        """
        pass
