class VitalSignMetric {
  final double? value;
  final String unit;
  final double confidence;
  final String status;
  final String? uncertaintyRange;
  final bool isExperimental;
  final String? disclaimer;

  VitalSignMetric({
    this.value,
    required this.unit,
    required this.confidence,
    required this.status,
    this.uncertaintyRange,
    this.isExperimental = false,
    this.disclaimer,
  });

  factory VitalSignMetric.fromJson(Map<String, dynamic> json) {
    return VitalSignMetric(
      value: (json['value'] as num?)?.toDouble(),
      unit: json['unit'] ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      status: json['status'] ?? 'N/A',
      uncertaintyRange: json['uncertainty_range'],
      isExperimental: json['is_experimental'] ?? false,
      disclaimer: json['disclaimer'],
    );
  }
}

class DashboardData {
  final String sessionId;
  final String timestamp;
  final String cameraType;
  final VitalSignMetric heartRate;
  final VitalSignMetric respiratoryRate;
  final VitalSignMetric oxygenSaturation;
  final VitalSignMetric bloodPressureSbp;
  final VitalSignMetric bloodPressureDbp;
  final double signalQualityScore;
  final String signalQualityStatus;
  final String qualityGuidance;
  final List<double> rppgWaveform;

  DashboardData({
    required this.sessionId,
    required this.timestamp,
    required this.cameraType,
    required this.heartRate,
    required this.respiratoryRate,
    required this.oxygenSaturation,
    required this.bloodPressureSbp,
    required this.bloodPressureDbp,
    required this.signalQualityScore,
    required this.signalQualityStatus,
    required this.qualityGuidance,
    required this.rppgWaveform,
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) {
    return DashboardData(
      sessionId: json['session_id'] ?? '',
      timestamp: json['timestamp'] ?? '',
      cameraType: json['camera_type'] ?? 'front_camera',
      heartRate: VitalSignMetric.fromJson(json['heart_rate'] ?? {}),
      respiratoryRate: VitalSignMetric.fromJson(json['respiratory_rate'] ?? {}),
      oxygenSaturation: VitalSignMetric.fromJson(json['oxygen_saturation'] ?? {}),
      bloodPressureSbp: VitalSignMetric.fromJson(json['blood_pressure_sbp'] ?? {}),
      bloodPressureDbp: VitalSignMetric.fromJson(json['blood_pressure_dbp'] ?? {}),
      signalQualityScore: (json['signal_quality_score'] as num?)?.toDouble() ?? 0.0,
      signalQualityStatus: json['signal_quality_status'] ?? 'POOR',
      qualityGuidance: json['quality_guidance'] ?? '',
      rppgWaveform: (json['rppg_waveform'] as List<dynamic>?)
              ?.map((e) => (e as num).toDouble())
              .toList() ??
          [],
    );
  }
}

class SessionListItem {
  final String id;
  final String createdAt;
  final double durationSec;
  final String status;
  final double? hrBpm;
  final double? rrBrpm;
  final double? spo2Percent;
  final double? sbpMmhg;
  final double? dbpMmhg;
  final String sqiStatus;

  SessionListItem({
    required this.id,
    required this.createdAt,
    required this.durationSec,
    required this.status,
    this.hrBpm,
    this.rrBrpm,
    this.spo2Percent,
    this.sbpMmhg,
    this.dbpMmhg,
    required this.sqiStatus,
  });

  factory SessionListItem.fromJson(Map<String, dynamic> json) {
    return SessionListItem(
      id: json['id'] ?? '',
      createdAt: json['created_at'] ?? '',
      durationSec: (json['duration_sec'] as num?)?.toDouble() ?? 0.0,
      status: json['status'] ?? 'UNKNOWN',
      hrBpm: (json['hr_bpm'] as num?)?.toDouble(),
      rrBrpm: (json['rr_brpm'] as num?)?.toDouble(),
      spo2Percent: (json['spo2_percent'] as num?)?.toDouble(),
      sbpMmhg: (json['sbp_mmhg'] as num?)?.toDouble(),
      dbpMmhg: (json['dbp_mmhg'] as num?)?.toDouble(),
      sqiStatus: json['sqi_status'] ?? 'N/A',
    );
  }
}
