"""
Participant-Level Data Partitioning and Zero-Leakage Dataset Splitting.

Enforces Phase 2 Task 5:
- Guarantees zero subject leakage: no frames or recordings from the same individual
  can ever appear across training, validation, or independent test sets.
- Generates reproducible, cryptographically hashed participant splits using controlled random seeds.
- Supports both Intra-Dataset Partitioning (Train/Val/Test) and Cross-Dataset Evaluation
  (e.g., Train on UBFC, Test on PURE).
"""

from typing import Dict, Any, List, Tuple, Set, Optional
import os
import hashlib
import json
import numpy as np


class ZeroLeakageDataSplitter:
    """
    Partitions datasets at the participant level to strictly eliminate cross-partition identity leakage.
    """

    def __init__(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
    ):
        if not np.isclose(train_ratio + val_ratio + test_ratio, 1.0):
            raise ValueError(f"Split ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio:.4f}")
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed

    def split_participants(
        self,
        participant_ids: List[str],
        stratify_by_skin_type: Optional[Dict[str, int]] = None,
    ) -> Dict[str, List[str]]:
        """
        Splits unique participant identifiers into Train, Validation, and Test sets.
        Ensures disjoint sets: Train ∩ Val = ∅, Train ∩ Test = ∅, Val ∩ Test = ∅.

        Args:
            participant_ids: List of unique subject strings (e.g., ['SUBJ-001', 'SUBJ-002', ...]).
            stratify_by_skin_type: Optional dictionary mapping participant_id -> Fitzpatrick skin type (1-6).
        """
        unique_subjects = sorted(list(set(participant_ids)))
        n_subjects = len(unique_subjects)

        if n_subjects < 3:
            raise ValueError(f"Minimum 3 unique participants required for 3-way split, got {n_subjects}")

        rng = np.random.RandomState(self.random_seed)

        if stratify_by_skin_type is not None:
            # Stratified splitting: group by skin type and sample proportionally
            groups: Dict[int, List[str]] = {}
            for s in unique_subjects:
                st = stratify_by_skin_type.get(s, 3)
                groups.setdefault(st, []).append(s)

            train_subj, val_subj, test_subj = [], [], []
            for st, members in sorted(groups.items()):
                shuffled = members.copy()
                rng.shuffle(shuffled)
                n = len(shuffled)
                n_tr = max(1, int(round(n * self.train_ratio))) if n >= 3 else 1
                n_v = max(1, int(round(n * self.val_ratio))) if n >= 3 else (1 if n >= 2 else 0)

                train_subj.extend(shuffled[:n_tr])
                val_subj.extend(shuffled[n_tr:n_tr + n_v])
                test_subj.extend(shuffled[n_tr + n_v:])
        else:
            # Deterministic shuffled split
            shuffled = unique_subjects.copy()
            rng.shuffle(shuffled)

            n_train = int(np.floor(n_subjects * self.train_ratio))
            n_val = int(np.floor(n_subjects * self.val_ratio))
            # Ensure at least 1 in val and test if possible
            if n_val == 0 and n_subjects >= 3:
                n_val = 1
                n_train = max(1, n_train - 1)

            train_subj = shuffled[:n_train]
            val_subj = shuffled[n_train:n_train + n_val]
            test_subj = shuffled[n_train + n_val:]

            # If test is empty due to rounding, shift one from train
            if len(test_subj) == 0 and len(train_subj) > 1:
                test_subj = [train_subj.pop()]

        # Verification: check disjointness
        s_train = set(train_subj)
        s_val = set(val_subj)
        s_test = set(test_subj)

        assert len(s_train.intersection(s_val)) == 0, "Leakage detected between Train and Val!"
        assert len(s_train.intersection(s_test)) == 0, "Leakage detected between Train and Test!"
        assert len(s_val.intersection(s_test)) == 0, "Leakage detected between Val and Test!"

        split_dict = {
            "train": sorted(train_subj),
            "val": sorted(val_subj),
            "test": sorted(test_subj),
        }

        return split_dict

    def map_recordings_to_split(
        self,
        recordings: List[Dict[str, Any]],
        split_dict: Dict[str, List[str]],
        participant_key: str = "participant_id",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Maps video recording objects to their respective partitions based on participant ID.
        """
        train_subjs = set(split_dict["train"])
        val_subjs = set(split_dict["val"])
        test_subjs = set(split_dict["test"])

        partitioned: Dict[str, List[Dict[str, Any]]] = {
            "train": [],
            "val": [],
            "test": [],
            "unassigned": [],
        }

        for rec in recordings:
            p_id = rec.get(participant_key)
            if p_id in train_subjs:
                partitioned["train"].append(rec)
            elif p_id in val_subjs:
                partitioned["val"].append(rec)
            elif p_id in test_subjs:
                partitioned["test"].append(rec)
            else:
                partitioned["unassigned"].append(rec)

        return partitioned

    @staticmethod
    def compute_split_hash(split_dict: Dict[str, List[str]], seed: int) -> str:
        """
        Computes a cryptographic SHA-256 fingerprint of the split for audit logging.
        Ensures exact reproducibility across experiment runs.
        """
        payload = {
            "seed": seed,
            "train": split_dict["train"],
            "val": split_dict["val"],
            "test": split_dict["test"],
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def define_cross_dataset_splits(
        available_datasets: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Defines standard cross-dataset benchmark configurations.
        Evaluates domain generalizability without cross-dataset training leakage.
        """
        benchmarks = [
            {
                "protocol": "Cross-Dataset-1",
                "name": "Train UBFC -> Test PURE",
                "train_dataset": "UBFC-rPPG",
                "test_dataset": "PURE",
                "investigates": "Domain shift from uncompressed raw video (UBFC) to lossless PNG sequences (PURE)",
            },
            {
                "protocol": "Cross-Dataset-2",
                "name": "Train PURE -> Test COHFACE",
                "train_dataset": "PURE",
                "test_dataset": "COHFACE",
                "investigates": "Robustness against heavy temporal MPEG-4 video compression artifacts",
            },
            {
                "protocol": "Cross-Dataset-3",
                "name": "Train VIPL-HR -> Test UBFC-rPPG",
                "train_dataset": "VIPL-HR",
                "test_dataset": "UBFC-rPPG",
                "investigates": "Generalization from multi-device smartphone data to desktop webcams",
            },
        ]
        return [b for b in benchmarks if b["train_dataset"] in available_datasets and b["test_dataset"] in available_datasets]

