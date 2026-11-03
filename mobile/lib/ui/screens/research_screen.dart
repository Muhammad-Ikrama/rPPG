import 'dart:math';
import 'package:flutter/material.dart';
import '../../services/api_service.dart';
import '../theme.dart';

class ResearchScreen extends StatefulWidget {
  const ResearchScreen({Key? key}) : super(key: key);

  @override
  State<ResearchScreen> createState() => _ResearchScreenState();
}

class _ResearchScreenState extends State<ResearchScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final ApiService _api = ApiService();

  bool _isLoading = false;
  String? _errorMessage;

  // Comparison state
  Map<String, dynamic>? _compareResults;
  double _refHr = 72.0;

  // DL experiments state
  List<dynamic> _experiments = [];

  // Cohort state
  Map<String, dynamic>? _cohortData;
  Map<String, dynamic>? _validationResults;

  // Datasets state
  List<dynamic> _datasets = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _initAndLoad();
  }

  Future<void> _initAndLoad() async {
    await _api.init();
    _loadExperiments();
    _loadDatasets();
    _loadCohortRecordings();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _runAlgorithmComparison() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      // Synthesize 5 seconds of physiological RGB traces at 30 fps (150 frames)
      const fps = 30.0;
      const nFrames = 150;
      final freq = _refHr / 60.0;
      final List<List<double>> rgb = [];

      final rand = Random();
      for (int i = 0; i < nFrames; i++) {
        final t = i / fps;
        final pulse = sin(2.0 * pi * freq * t);
        final noise = (rand.nextDouble() - 0.5) * 0.5;
        rgb.add([
          180.0 + 2.0 * pulse + noise,
          120.0 + 4.5 * pulse + noise,
          95.0 + 1.2 * pulse + noise,
        ]);
      }

      final res = await _api.compareAllAlgorithms(
        rgbSignals: rgb,
        fps: fps,
        referenceHrBpm: _refHr,
      );

      setState(() {
        _compareResults = res;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _loadExperiments() async {
    try {
      final res = await _api.getExperiments();
      setState(() {
        _experiments = res;
      });
    } catch (_) {}
  }

  Future<void> _loadDatasets() async {
    try {
      final res = await _api.getDatasetCompatibility();
      setState(() {
        _datasets = res['datasets'] as List<dynamic>? ?? [];
      });
    } catch (_) {}
  }

  Future<void> _loadCohortRecordings() async {
    try {
      final res = await _api.getCohortRecordings();
      setState(() {
        _cohortData = res;
      });
    } catch (_) {}
  }

  Future<void> _triggerValidation() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final res = await _api.runCohortValidation();
      setState(() {
        _validationResults = res;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Biomedical Research Lab'),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          indicatorColor: BiomedicalTheme.accentTeal,
          tabs: const [
            Tab(icon: Icon(Icons.compare_arrows), text: 'Algorithms'),
            Tab(icon: Icon(Icons.psychology), text: 'Deep Learning'),
            Tab(icon: Icon(Icons.groups), text: '50-Subj Cohort'),
            Tab(icon: Icon(Icons.dataset), text: 'Datasets'),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: BiomedicalTheme.accentTeal))
          : TabBarView(
              controller: _tabController,
              children: [
                _buildAlgorithmComparisonTab(),
                _buildDeepLearningTab(),
                _buildCohortValidationTab(),
                _buildDatasetsTab(),
              ],
            ),
    );
  }

  // 1. Multi-Algorithm Head-to-Head Comparison Tab
  Widget _buildAlgorithmComparisonTab() {
    final algos = _compareResults?['algorithms'] as Map<String, dynamic>?;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Traditional vs. Deep Learning',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  Text('POS, CHROM, GREEN, ICA vs. PhysNet 3D-CNN',
                      style: TextStyle(fontSize: 12, color: Colors.white.withOpacity(0.6))),
                ],
              ),
              ElevatedButton.icon(
                onPressed: _runAlgorithmComparison,
                icon: const Icon(Icons.play_arrow, size: 16),
                label: const Text('Compare', style: TextStyle(fontSize: 12)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: BiomedicalTheme.accentTeal,
                  foregroundColor: BiomedicalTheme.backgroundDark,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (_errorMessage != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.red),
              ),
              child: Text(_errorMessage!, style: const TextStyle(color: Colors.redAccent)),
            ),
          if (algos == null)
            Container(
              padding: const EdgeInsets.all(24),
              alignment: Alignment.center,
              child: Column(
                children: [
                  Icon(Icons.analytics_outlined, size: 48, color: Colors.white.withOpacity(0.3)),
                  const SizedBox(height: 12),
                  const Text(
                    'Tap "Compare" to run multi-algorithm benchmark.\nEvaluates signal-to-noise ratio, execution latency, and HR accuracy.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: BiomedicalTheme.textMuted, fontSize: 13),
                  ),
                ],
              ),
            )
          else ...[
            ...algos.entries.map((e) {
              final name = e.key;
              final data = e.value as Map<String, dynamic>;
              final hr = data['heart_rate_bpm'];
              final snr = data['snr_db'];
              final latency = data['execution_time_ms'] ?? data['latency_ms'];
              final error = data['error_against_reference_bpm'] ?? data['error_bpm'];
              final isDL = name.contains('Deep Learning');

              return Card(
                color: BiomedicalTheme.cardNavy,
                margin: const EdgeInsets.only(bottom: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side: BorderSide(
                    color: isDL ? BiomedicalTheme.accentTeal : Colors.white.withOpacity(0.08),
                    width: isDL ? 1.5 : 1.0,
                  ),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(name,
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 15,
                                color: isDL ? BiomedicalTheme.accentTeal : Colors.white,
                              )),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: isDL
                                  ? BiomedicalTheme.accentTeal.withOpacity(0.2)
                                  : Colors.white.withOpacity(0.08),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              isDL ? 'Neural 3D-CNN' : 'Color Space Projection',
                              style: TextStyle(
                                fontSize: 10,
                                color: isDL ? BiomedicalTheme.accentTeal : Colors.white70,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          _statTile('Estimated HR', hr != null ? '$hr BPM' : 'N/A'),
                          _statTile('SNR', snr != null ? '$snr dB' : 'N/A'),
                          _statTile('Latency', latency != null ? '$latency ms' : 'N/A'),
                          _statTile(
                            'Abs Error',
                            error != null ? '${error.abs().toStringAsFixed(1)} BPM' : 'N/A',
                            valueColor: error != null && error.abs() < 3.0
                                ? BiomedicalTheme.accentGreen
                                : BiomedicalTheme.accentAmber,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ],
        ],
      ),
    );
  }

  // 2. Deep Learning Models & Experiments Tab
  Widget _buildDeepLearningTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Registered DL Checkpoints',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              IconButton(
                icon: const Icon(Icons.refresh, size: 20),
                onPressed: _loadExperiments,
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_experiments.isEmpty)
            Container(
              padding: const EdgeInsets.all(24),
              alignment: Alignment.center,
              child: const Text('No training runs registered yet.',
                  style: TextStyle(color: BiomedicalTheme.textMuted)),
            )
          else
            ..._experiments.map((exp) {
              final arch = exp['model_architecture'] ?? 'PhysNet';
              final date = exp['timestamp'] ?? '';
              final valLoss = exp['final_val_loss'];
              final onnx = exp['onnx_export_path'] != null;

              return Card(
                color: BiomedicalTheme.cardNavy,
                margin: const EdgeInsets.only(bottom: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(arch, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                          if (onnx)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: BiomedicalTheme.accentGreen.withOpacity(0.2),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: const Text('ONNX Exported',
                                  style: TextStyle(color: BiomedicalTheme.accentGreen, fontSize: 10)),
                            ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text('Recorded: $date',
                          style: TextStyle(fontSize: 11, color: Colors.white.withOpacity(0.5))),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          _statTile('Epochs', '${exp['epochs_completed'] ?? 3}'),
                          _statTile('Validation Loss', valLoss != null ? '$valLoss' : 'N/A'),
                          _statTile('Loss Function', 'Neg Pearson + Cos Spectral'),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
        ],
      ),
    );
  }

  // 3. 50-Participant Cohort Validation Tab
  Widget _buildCohortValidationTab() {
    final stats = _cohortData?['coverage_statistics'] as Map<String, dynamic>?;
    final totalRec = _cohortData?['total_recordings'] ?? 0;
    final valParams = _validationResults?['parameters'] as Map<String, dynamic>?;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('50-Subject Validation Cohort',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  Text('$totalRec Paired Clinical Recordings',
                      style: TextStyle(fontSize: 12, color: Colors.white.withOpacity(0.6))),
                ],
              ),
              ElevatedButton.icon(
                onPressed: _triggerValidation,
                icon: const Icon(Icons.biotech, size: 16),
                label: const Text('Validate All', style: TextStyle(fontSize: 12)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: BiomedicalTheme.accentTeal,
                  foregroundColor: BiomedicalTheme.backgroundDark,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (stats != null) ...[
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: BiomedicalTheme.cardNavy,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Participant Diversity Coverage',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text(
                    'Fitzpatrick Skin Types: ${stats['fitzpatrick_distribution']}\n'
                    'Lighting Conditions: ${stats['lighting_distribution']}',
                    style: const TextStyle(fontSize: 11, color: BiomedicalTheme.textMuted),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],
          if (valParams != null) ...[
            const Text('Clinical Agreement (Bland-Altman / ISO 81060-2)',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            ...valParams.entries.map((e) {
              final pName = e.key.toUpperCase();
              final pData = e.value as Map<String, dynamic>;
              final ba = pData['bland_altman'] as Map<String, dynamic>?;

              return Card(
                color: BiomedicalTheme.cardNavy,
                margin: const EdgeInsets.only(bottom: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(pName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                          Text(pData['unit'] ?? '',
                              style: const TextStyle(color: BiomedicalTheme.accentTeal, fontSize: 12)),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          _statTile('Bias', '${pData['mean_error_bias']}'),
                          _statTile('MAE', '${pData['mae']}'),
                          _statTile('RMSE', '${pData['rmse']}'),
                          _statTile('Pearson r', '${pData['pearson_r']}'),
                        ],
                      ),
                      if (ba != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          '95% Limits of Agreement (LOA): [${ba['lower_loa']} to ${ba['upper_loa']}]',
                          style: TextStyle(fontSize: 11, color: Colors.white.withOpacity(0.7)),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }).toList(),
          ],
        ],
      ),
    );
  }

  // 4. Benchmark Datasets Matrix Tab
  Widget _buildDatasetsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Dataset Ground-Truth Compatibility',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          const Text(
            'Matrix auditing which datasets support HR, RR, SpO2, and BP references.',
            style: TextStyle(fontSize: 12, color: BiomedicalTheme.textMuted),
          ),
          const SizedBox(height: 16),
          if (_datasets.isEmpty)
            const Center(child: Text('Loading dataset matrix...'))
          else
            ..._datasets.map((d) {
              final name = d['name'];
              final subjects = d['participants_count'];
              final hr = d['hr_labels_available'] == true;
              final rr = d['rr_labels_available'] == true;
              final spo2 = d['spo2_labels_available'] == true;
              final bp = d['bp_labels_available'] == true;

              return Card(
                color: BiomedicalTheme.cardNavy,
                margin: const EdgeInsets.only(bottom: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                          Text('$subjects Subjects',
                              style: const TextStyle(color: BiomedicalTheme.accentTeal, fontSize: 12)),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _labelBadge('HR', hr),
                          _labelBadge('RR', rr),
                          _labelBadge('SpO2', spo2),
                          _labelBadge('BP', bp),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
        ],
      ),
    );
  }

  Widget _statTile(String label, String value, {Color? valueColor}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 10, color: BiomedicalTheme.textMuted)),
        const SizedBox(height: 2),
        Text(value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: valueColor ?? Colors.white,
            )),
      ],
    );
  }

  Widget _labelBadge(String label, bool supported) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: supported
            ? BiomedicalTheme.accentGreen.withOpacity(0.15)
            : Colors.red.withOpacity(0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: supported ? BiomedicalTheme.accentGreen : Colors.redAccent.withOpacity(0.4),
        ),
      ),
      child: Text(
        '$label: ${supported ? "YES" : "NO"}',
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: supported ? BiomedicalTheme.accentGreen : Colors.redAccent,
        ),
      ),
    );
  }
}

