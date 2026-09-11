from dataclasses import dataclass, field


@dataclass
class ValidationMessage:
    level: str
    message: str


@dataclass
class ValidationReport:
    messages: list[ValidationMessage] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.messages.append(ValidationMessage("ERROR", message))

    def add_warning(self, message: str) -> None:
        self.messages.append(ValidationMessage("WARNING", message))

    def add_info(self, message: str) -> None:
        self.messages.append(ValidationMessage("INFO", message))

    @property
    def errors(self):
        return [m for m in self.messages if m.level == "ERROR"]

    @property
    def warnings(self):
        return [m for m in self.messages if m.level == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def __str__(self) -> str:
        if not self.messages:
            return "No validation messages."
        return "\n".join(f"[{m.level}] {m.message}" for m in self.messages)
