"""
Public rPPG Dataset Compatibility Table and Research Metadata.

Documents available ground-truth physiological modalities across benchmark datasets.
Prevents false assumptions regarding dataset capabilities (e.g. absent BP/RR labels).
"""

from typing import Dict, Any, List

DATASET_COMPATIBILITY_MATRIX: Dict[str, Dict[str, Any]] = {
    "UBFC-rPPG": {
        "full_name": "University of Bourgogne Franche-Comté rPPG Dataset",
        "reference": "Bobbia et al., Computer Vision and Image Understanding, 2019",
        "subjects_count": 42,
        "acquisition_sensor": "Logitech C920 HD Pro Webcam (640x480, 30 fps)",
        "illumination": "Ambient indoor office fluorescent lighting",
        "ground_truth_device": "Contec Medical CMS50E Pulse Oximeter",
        "supported_parameters": {
            "heart_rate_hr": {
                "available": True,
                "modality": "Pulse oximeter continuous BVP signal and instantaneous HR",
                "sampling_rate_hz": 60.0,
            },
            "respiratory_rate_rr": {
                "available": False,
                "modality": "None (No thoracic chest belt or capnography reference)",
            },
            "oxygen_saturation_spo2": {
                "available": True,
                "modality": "Pulse oximeter discrete SpO2 readings (normoxic baseline ~97-99%)",
            },
            "blood_pressure_bp": {
                "available": False,
                "modality": "None (No arterial catheter or oscillometric cuff paired data)",
            },
        },
        "license": "Academic research use upon agreement with Univ Bourgogne",
        "primary_benchmark_use": "POS algorithm HR estimation and waveform morphology validation",
    },
    "PURE": {
        "full_name": "Pulse Rate Estimation from Facial Videos",
        "reference": "Stricker et al., Biomedical Optics Express, 2014",
        "subjects_count": 10,
        "acquisition_sensor": "Eco274CVGE industrial RGB camera (640x480 @ 30 fps, uncompressed PNG)",
        "illumination": "Controlled halogen lighting",
        "ground_truth_device": "CMS50E transmissive finger pulse oximeter",
        "supported_parameters": {
            "heart_rate_hr": {
                "available": True,
                "modality": "PPG waveform and pulse rate (60 Hz)",
            },
            "respiratory_rate_rr": {
                "available": False,
                "modality": "None (No respiratory reference)",
            },
            "oxygen_saturation_spo2": {
                "available": True,
                "modality": "Finger clip SpO2 time-series (60 Hz)",
            },
            "blood_pressure_bp": {
                "available": False,
                "modality": "None",
            },
        },
        "license": "Available for academic research",
        "primary_benchmark_use": "Head motion robustness (steady, talking, translation, rotation)",
    },
    "COHFACE": {
        "full_name": "Idiap COHFACE Dataset",
        "reference": "Heusch et al., Idiap Research Report, 2017",
        "subjects_count": 40,
        "acquisition_sensor": "Logitech HD C525 (640x480 @ 20 fps, heavily compressed MPEG-4)",
        "illumination": "Studio lighting and natural ambient light",
        "ground_truth_device": "Thought Technology BioGraph Infiniti (Blood Volume Pulse + Respiration Belt)",
        "supported_parameters": {
            "heart_rate_hr": {
                "available": True,
                "modality": "Continuous finger BVP (256 Hz)",
            },
            "respiratory_rate_rr": {
                "available": True,
                "modality": "Thoracic respiration strain gauge belt (256 Hz)",
            },
            "oxygen_saturation_spo2": {
                "available": False,
                "modality": "None",
            },
            "blood_pressure_bp": {
                "available": False,
                "modality": "None",
            },
        },
        "license": "Idiap Research Institute agreement",
        "primary_benchmark_use": "Compression artifacts impact on HR and Respiratory Rate (RR)",
    },
    "VIPL-HR": {
        "full_name": "Visual-optical physiological Laboratory Heart Rate Dataset",
        "reference": "Niu et al., IEEE Transactions on Pattern Analysis and Machine Intelligence, 2019",
        "subjects_count": 107,
        "acquisition_sensor": "Webcam, smartphone (front/rear), and RealSense F200 (RGB-D)",
        "illumination": "9 diverse scenarios (dim, bright, uneven, motion)",
        "ground_truth_device": "Contec CMS60C BVP and blood oxygen saturation sensor",
        "supported_parameters": {
            "heart_rate_hr": {
                "available": True,
                "modality": "Continuous BVP and HR (50 Hz)",
            },
            "respiratory_rate_rr": {
                "available": False,
                "modality": "None",
            },
            "oxygen_saturation_spo2": {
                "available": True,
                "modality": "Contec finger sensor SpO2",
            },
            "blood_pressure_bp": {
                "available": False,
                "modality": "None",
            },
        },
        "license": "VIPL Lab academic license",
        "primary_benchmark_use": "Cross-device smartphone vs webcam rPPG evaluation",
    },
    "MMPD": {
        "full_name": "Multi-Domain Mobile Video Physiology Dataset",
        "reference": "Tang et al., NeurIPS, 2023",
        "subjects_count": 33,
        "acquisition_sensor": "Samsung Galaxy S22 Ultra mobile phone (1280x720 @ 30 fps)",
        "illumination": "4 illumination conditions (LED, incandescent, fluorescent, natural)",
        "ground_truth_device": "HKH-11C finger pulse sensor",
        "supported_parameters": {
            "heart_rate_hr": {
                "available": True,
                "modality": "PPG waveform and HR (200 Hz)",
            },
            "respiratory_rate_rr": {
                "available": True,
                "modality": "Derived PPG respiration index",
            },
            "oxygen_saturation_spo2": {
                "available": True,
                "modality": "Continuous pulse oximeter SpO2",
            },
            "blood_pressure_bp": {
                "available": False,
                "modality": "None (No paired oscillometric blood pressure)",
            },
        },
        "license": "Open access for research",
        "primary_benchmark_use": "Fitzpatrick skin tone diversity (types 3-6) and mobile camera optics",
    },
}


def get_compatibility_summary() -> List[Dict[str, Any]]:
    """Returns a tabular list of dataset compatibility for API/UI display."""
    summary = []
    for name, data in DATASET_COMPATIBILITY_MATRIX.items():
        params = data["supported_parameters"]
        summary.append({
            "name": name,
            "full_name": data["full_name"],
            "subjects": data["subjects_count"],
            "sensor": data["acquisition_sensor"],
            "ground_truth_device": data["ground_truth_device"],
            "hr_available": params["heart_rate_hr"]["available"],
            "rr_available": params["respiratory_rate_rr"]["available"],
            "spo2_available": params["oxygen_saturation_spo2"]["available"],
            "bp_available": params["blood_pressure_bp"]["available"],
            "license": data["license"],
            "primary_benchmark_use": data["primary_benchmark_use"],
        })
    return summary
