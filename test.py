from dataclasses import dataclass

@dataclass
class User:
    id: int
    nick: str

    def __eq__(self, other) -> bool:
        return self.id == other.id
    
    def __hash__(self) -> int:
        return self.id
    
print(set([User(1, "s"), User(2, "y")]))