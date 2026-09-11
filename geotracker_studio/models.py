from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import pandas as pd

from .validation import ValidationReport


@dataclass
class Session:
    """In-memory representation of one GeoTracker recording session."""

    path: Path
    metadata: dict[str, str]
    samples: pd.DataFrame
    waypoints: pd.DataFrame
    events: pd.DataFrame
    validation: ValidationReport
    statistics: dict[str, Any] = field(default_factory=dict)

    @property
    def session_id(self) -> str:
        return self.metadata.get("session_id", self.path.name)

    @property
    def schema_version(self) -> str:
        return self.metadata.get("schema_version", "")

    @property
    def gps_samples(self) -> pd.DataFrame:
        if "gps_valid" not in self.samples:
            return self.samples.iloc[0:0].copy()
        return self.samples[self.samples["gps_valid"].fillna(False)].copy()

    @property
    def gps_updates(self) -> pd.DataFrame:
        if not {"gps_valid", "gps_updated"}.issubset(self.samples.columns):
            return self.samples.iloc[0:0].copy()
        mask = (
            self.samples["gps_valid"].fillna(False)
            & self.samples["gps_updated"].fillna(False)
        )
        return self.samples[mask].copy()

    @property
    def environment_samples(self) -> pd.DataFrame:
        if "bme_valid" not in self.samples:
            return self.samples.iloc[0:0].copy()
        return self.samples[self.samples["bme_valid"].fillna(False)].copy()

    @property
    def magnetometer_samples(self) -> pd.DataFrame:
        if "mag_valid" not in self.samples:
            return self.samples.iloc[0:0].copy()
        return self.samples[self.samples["mag_valid"].fillna(False)].copy()

    @property
    def imu_samples(self) -> pd.DataFrame:
        if "imu_valid" not in self.samples:
            return self.samples.iloc[0:0].copy()
        return self.samples[self.samples["imu_valid"].fillna(False)].copy()
