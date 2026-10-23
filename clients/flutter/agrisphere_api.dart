// AgriSphere FairMarket API client (Flutter/Dart).
// pubspec.yaml-e add korun:   http: ^1.2.0
// Use:
//   final api = AgriSphereApi('https://<RENDER_URL>');       // default language: 'bn'
//   api.lang = 'en';                                         // language switch: backend-er shob text ei bhashay ashe
//   await api.health();                                   // app open-e (server ghumay, 30-50 sec lage)
//   await api.login(phone: '017...', password: '...');   // token auto save hoy (api.token)
//   final d = await api.decide(crop: 'tomato', quantityKg: 500, grade: 'A', market: 'Dhaka');
//   print(d['recommended']);
// Error: ApiException(status, message) - e.status 401 hole abar login korte bolun.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final int status; // 0 = network/timeout
  final String message;
  ApiException(this.status, this.message);
  bool get isUnauthorized => status == 401;
  @override
  String toString() => 'ApiException($status): $message';
}

class AgriSphereApi {
  AgriSphereApi(String baseUrl, {this.token, this.lang = 'bn', http.Client? client})
      : baseUrl = baseUrl.replaceAll(RegExp(r'/+$'), ''),
        _client = client ?? http.Client();

  final String baseUrl;
  String? token;
  String lang; // 'bn' | 'en' -> Accept-Language header (backend-er message/label/explanation ei bhashay ashe)
  final http.Client _client;
  static const _timeout = Duration(seconds: 60);

  // ---------------------------------------------------------------- core
  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept-Language': lang,
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Uri _uri(String path, [Map<String, String?>? query]) {
    final q = <String, String>{};
    query?.forEach((k, v) {
      if (v != null) q[k] = v;
    });
    return Uri.parse('$baseUrl$path').replace(queryParameters: q.isEmpty ? null : q);
  }

  String _message(dynamic data) {
    if (data is Map && data['detail'] != null) {
      final d = data['detail'];
      if (d is String) return d;
      if (d is List) {
        return d
            .map((e) => e is Map ? '${(e['loc'] is List && (e['loc'] as List).isNotEmpty) ? (e['loc'] as List).last : ''}: ${e['msg']}' : '$e')
            .join('; ');
      }
    }
    return 'Something went wrong';
  }

  dynamic _decode(http.Response r) {
    final body = utf8.decode(r.bodyBytes);
    dynamic data;
    try {
      data = body.isEmpty ? null : jsonDecode(body);
    } catch (_) {
      data = body;
    }
    if (r.statusCode >= 200 && r.statusCode < 300) return data;
    throw ApiException(r.statusCode, _message(data));
  }

  Future<dynamic> _send(Future<http.Response> Function() call) async {
    try {
      final r = await call().timeout(_timeout);
      return _decode(r);
    } on ApiException {
      rethrow;
    } on TimeoutException {
      throw ApiException(0, 'Server shara dichhe na (timeout). Abar chesta korun.');
    } catch (e) {
      throw ApiException(0, 'Network problem: $e');
    }
  }

  Future<dynamic> _get(String path, [Map<String, String?>? q]) =>
      _send(() => _client.get(_uri(path, q), headers: _headers));

  Future<dynamic> _put(String path, Map<String, dynamic> body) =>
      _send(() => _client.put(_uri(path), headers: _headers, body: jsonEncode(body)));

  Future<dynamic> _post(String path, [Map<String, dynamic>? body, Map<String, String?>? q]) =>
      _send(() => _client.post(_uri(path, q), headers: _headers, body: jsonEncode(body ?? {})));

  Future<Map<String, dynamic>> _getM(String p, [Map<String, String?>? q]) async =>
      Map<String, dynamic>.from(await _get(p, q) as Map);
  Future<List<dynamic>> _getL(String p, [Map<String, String?>? q]) async =>
      List<dynamic>.from(await _get(p, q) as List);
  Future<Map<String, dynamic>> _postM(String p, [Map<String, dynamic>? b, Map<String, String?>? q]) async =>
      Map<String, dynamic>.from(await _post(p, b, q) as Map);

  // ---------------------------------------------------------------- helpers
  static Map<String, dynamic> district(String d) => {'district': d};
  static Map<String, dynamic> latLon(double lat, double lon) => {'lat': lat, 'lon': lon};

  // ---------------------------------------------------------------- system / auth
  Future<Map<String, dynamic>> health() => _getM('/health');
  Future<Map<String, dynamic>> meta() => _getM('/meta'); // crops, markets, grades (dropdown-er jonno)

  /// role = 'farmer' | 'buyer'. Response-er user_id = farmer_id / buyer_id.
  Future<Map<String, dynamic>> register({
    required String name,
    required String phone,
    required String password,
    required String role,
    String district = 'Dhaka',
    String? orgType,
  }) async {
    final r = await _postM('/auth/register', {
      'name': name,
      'phone': phone,
      'password': password,
      'role': role,
      'district': district,
      if (orgType != null) 'org_type': orgType,
    });
    token = r['token'] as String;
    return r;
  }

  Future<Map<String, dynamic>> login({required String phone, required String password}) async {
    final r = await _postM('/auth/login', {'phone': phone, 'password': password});
    token = r['token'] as String;
    return r;
  }

  Future<Map<String, dynamic>> me() => _getM('/auth/me');
  Future<Map<String, dynamic>> updateMe({String? name, String? district, String? phone}) => _put('/auth/me', {
        if (name != null) 'name': name,
        if (district != null) 'district': district,
        if (phone != null) 'phone': phone,
      }).then((d) => Map<String, dynamic>.from(d as Map));
  void logout() => token = null;

  // ---------------------------------------------------------------- MAIN decision engine
  Future<Map<String, dynamic>> decide({
    required String crop,
    required double quantityKg,
    String grade = 'B',
    String market = 'Dhaka',
    String? lotId,
    double? currentPrice,
    Map<String, double>? costs, // transport_per_kg_km, handling_per_kg, storage_per_kg_day, commission_pct, local_market_km
    double? temperatureC,
    double? spoilagePerDay, // 0.02 = din-e 2% nosto
    Map<String, dynamic>? farmerLocation,
    List<Map<String, dynamic>>? offers,
  }) =>
      _postM('/decision/net-profit', {
        'crop': crop,
        'quantity_kg': quantityKg,
        'grade': grade,
        'market': market,
        if (lotId != null) 'lot_id': lotId,
        if (currentPrice != null) 'current_price': currentPrice,
        if (costs != null) 'costs': costs,
        if (temperatureC != null) 'temperature_c': temperatureC,
        if (spoilagePerDay != null) 'spoilage_per_day': spoilagePerDay,
        if (farmerLocation != null) 'farmer_location': farmerLocation,
        if (offers != null) 'offers': offers,
      });

  Future<Map<String, dynamic>> forecast(String crop, {String market = 'Dhaka'}) =>
      _getM('/forecast', {'crop': crop, 'market': market});

  // ---------------------------------------------------------------- grading, batch, lot
  /// bytes = photo-r bytes (image_picker: await file.readAsBytes()).
  Future<Map<String, dynamic>> grade(Uint8List bytes, {String filename = 'photo.jpg'}) async {
    final d = await _send(() async {
      final req = http.MultipartRequest('POST', _uri('/grade'));
      req.headers['Accept-Language'] = lang;
      if (token != null) req.headers['Authorization'] = 'Bearer $token';
      req.files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
      return http.Response.fromStream(await _client.send(req));
    });
    return Map<String, dynamic>.from(d as Map);
  }

  Future<Map<String, dynamic>> createBatch({
    required String farmerId,
    required String crop,
    required double quantityKg,
    required Map<String, dynamic> location,
    required String grade,
    double? gradeConfidence,
    String? harvestDate, // 'YYYY-MM-DD'
    String? photoBase64, // chhoto thumbnail (<=400KB)
    String? photoUrl,
  }) =>
      _postM('/batches', {
        'farmer_id': farmerId,
        'crop': crop,
        'quantity_kg': quantityKg,
        'location': location,
        'grade': grade,
        if (gradeConfidence != null) 'grade_confidence': gradeConfidence,
        if (harvestDate != null) 'harvest_date': harvestDate,
        if (photoBase64 != null) 'photo_base64': photoBase64,
        if (photoUrl != null) 'photo_url': photoUrl,
      });

  Future<Map<String, dynamic>> passport(String batchId) => _getM('/batches/$batchId/passport'); // qr_payload -> QR

  Future<Map<String, dynamic>> createLot({
    required String farmerId,
    required String crop,
    required double quantityKg,
    required String grade,
    required Map<String, dynamic> location,
    String? harvestDate,
    String? batchId,
  }) =>
      _postM('/lots', {
        'farmer_id': farmerId,
        'crop': crop,
        'quantity_kg': quantityKg,
        'grade': grade,
        'location': location,
        if (harvestDate != null) 'harvest_date': harvestDate,
        if (batchId != null) 'batch_id': batchId,
      });

  Future<List<dynamic>> listLots({String? crop, String? farmerId, String? status}) =>
      _getL('/lots', {'crop': crop, 'farmer_id': farmerId, 'status': status});
  Future<Map<String, dynamic>> getLot(String lotId) => _getM('/lots/$lotId');
  Future<Map<String, dynamic>> withdrawLot(String lotId) => _postM('/lots/$lotId/withdraw');

  /// EK CALL-E: photo -> grade -> save -> batch. Response: {grading:{grade,confidence,...}, batch:{id,...}, has_photo}
  Future<Map<String, dynamic>> batchFromPhoto(
    Uint8List bytes, {
    required String farmerId,
    required String crop,
    required double quantityKg,
    String district = 'Dhaka',
    double? lat,
    double? lon,
    String? harvestDate,
    String filename = 'photo.jpg',
  }) async {
    final d = await _send(() async {
      final req = http.MultipartRequest('POST', _uri('/batches/from-photo'));
      req.headers['Accept-Language'] = lang;
      if (token != null) req.headers['Authorization'] = 'Bearer $token';
      req.fields.addAll({
        'farmer_id': farmerId,
        'crop': crop,
        'quantity_kg': '$quantityKg',
        'district': district,
        if (lat != null) 'lat': '$lat',
        if (lon != null) 'lon': '$lon',
        if (harvestDate != null) 'harvest_date': harvestDate,
      });
      req.files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));
      return http.Response.fromStream(await _client.send(req));
    });
    return Map<String, dynamic>.from(d as Map);
  }

  Future<List<dynamic>> listBatches({String? farmerId}) => _getL('/batches', {'farmer_id': farmerId}); // photo chhara
  Future<Map<String, dynamic>> getBatch(String batchId) => _getM('/batches/$batchId'); // photo_base64 soho

  // ---------------------------------------------------------------- buyers, matching, pooling, orders
  Future<Map<String, dynamic>> createDemand({
    required String buyerId,
    required String crop,
    required double quantityKg,
    required double pricePerKg,
    required Map<String, dynamic> location,
    double? minQuantityKg,
    String minGrade = 'C',
    double maxDistanceKm = 300,
    String? neededBy,
    bool buyerPickup = false,
  }) =>
      _postM('/demands', {
        'buyer_id': buyerId,
        'crop': crop,
        'quantity_kg': quantityKg,
        'price_per_kg': pricePerKg,
        'location': location,
        if (minQuantityKg != null) 'min_quantity_kg': minQuantityKg,
        'min_grade': minGrade,
        'max_distance_km': maxDistanceKm,
        if (neededBy != null) 'needed_by': neededBy,
        'buyer_pickup': buyerPickup,
      });

  Future<List<dynamic>> listDemands({String? crop, String? buyerId, String? status}) =>
      _getL('/demands', {'crop': crop, 'buyer_id': buyerId, 'status': status});
  Future<Map<String, dynamic>> getDemand(String demandId) => _getM('/demands/$demandId');
  Future<Map<String, dynamic>> closeDemand(String demandId) => _postM('/demands/$demandId/close');

  /// Nijer order-gulo (login role onujayi auto filter). Admin: farmerId/buyerId/status diye filter.
  Future<List<dynamic>> listOrders({String? farmerId, String? buyerId, String? status}) =>
      _getL('/orders', {'farmer_id': farmerId, 'buyer_id': buyerId, 'status': status});

  // ---- price screens + dashboards
  Future<Map<String, dynamic>> priceHistory(String crop, {String market = 'Dhaka', int days = 60}) =>
      _getM('/prices/history', {'crop': crop, 'market': market, 'days': '$days'});
  Future<Map<String, dynamic>> pricesToday({String market = 'Dhaka'}) => _getM('/prices/today', {'market': market});
  Future<Map<String, dynamic>> farmerDashboard(String farmerId) => _getM('/dashboard/farmer/$farmerId');
  Future<Map<String, dynamic>> buyerDashboard(String buyerId) => _getM('/dashboard/buyer/$buyerId');
  Future<Map<String, dynamic>> adminDashboard() => _getM('/dashboard/admin');
  Future<Map<String, dynamic>> seedDemo() => _postM('/admin/seed-demo'); // admin only
  Future<List<dynamic>> lotOffers(String lotId) => _getL('/lots/$lotId/offers');
  Future<Map<String, dynamic>> buyerReliability(String buyerId) => _getM('/buyers/$buyerId/reliability');

  Future<Map<String, dynamic>> poolPlan(String demandId, {int harvestWindowDays = 4}) =>
      _postM('/pool/plan', {'demand_id': demandId, 'harvest_window_days': harvestWindowDays});

  /// allocations = poolPlan()['allocations'] hubohu.
  Future<Map<String, dynamic>> createOrder({
    required String demandId,
    required List<dynamic> allocations,
    required double agreedPrice,
    List<String> batchIds = const [],
  }) =>
      _postM('/orders', {
        'demand_id': demandId,
        'allocations': allocations,
        'agreed_price': agreedPrice,
        'batch_ids': batchIds,
      });

  Future<Map<String, dynamic>> getOrder(String orderId) => _getM('/orders/$orderId');

  Future<Map<String, dynamic>> recordDelivery(
    String orderId, {
    String? observedGrade,
    double? observedWeightKg,
    double proposedDeductionPct = 0,
    String reason = '',
  }) =>
      _postM('/orders/$orderId/delivery', {
        if (observedGrade != null) 'observed_grade': observedGrade,
        if (observedWeightKg != null) 'observed_weight_kg': observedWeightKg,
        'proposed_deduction_pct': proposedDeductionPct,
        'reason': reason,
      });

  Future<Map<String, dynamic>> evidence(String orderId) => _getM('/orders/$orderId/evidence');

  /// admin/human reviewer: resolved_for_buyer | resolved_against_buyer | resolved_split | no_fault
  Future<Map<String, dynamic>> resolveDispute(String orderId, String outcome) =>
      _postM('/orders/$orderId/dispute/resolve', null, {'outcome': outcome});

  /// action = fund | release | refund | cancel (SIMULATED payment)
  Future<Map<String, dynamic>> payment(String orderId, String action, {bool onTime = true, String? cancelledBy}) =>
      _postM('/orders/$orderId/payment', {
        'action': action,
        'on_time': onTime,
        if (cancelledBy != null) 'cancelled_by': cancelledBy,
      });

  // ---------------------------------------------------------------- negotiation, alerts, loss, weather, radar, assistant
  Future<Map<String, dynamic>> counterOffer({
    required String crop,
    required double quantityKg,
    String grade = 'B',
    String market = 'Dhaka',
    List<Map<String, dynamic>>? offers, // [{price_per_kg, distance_km, buyer_name}]
    String? lotId,
    double? productionCostPerKg,
    double marginPct = 0,
    Map<String, double>? costs,
    double? temperatureC,
    double? spoilagePerDay,
  }) =>
      _postM('/negotiation/counter-offer', {
        'crop': crop,
        'quantity_kg': quantityKg,
        'grade': grade,
        'market': market,
        if (offers != null) 'offers': offers,
        if (lotId != null) 'lot_id': lotId,
        if (productionCostPerKg != null) 'production_cost_per_kg': productionCostPerKg,
        'margin_pct': marginPct,
        if (costs != null) 'costs': costs,
        if (temperatureC != null) 'temperature_c': temperatureC,
        if (spoilagePerDay != null) 'spoilage_per_day': spoilagePerDay,
      });

  Future<Map<String, dynamic>> priceAlert(String crop, {String market = 'Dhaka'}) =>
      _getM('/alerts/price', {'crop': crop, 'market': market});
  Future<Map<String, dynamic>> alertsScan() => _getM('/alerts/scan');
  Future<Map<String, dynamic>> watchCrop(String farmerId, String crop, {String market = 'Dhaka', double thresholdPct = 7}) =>
      _postM('/alerts/watch', {'farmer_id': farmerId, 'crop': crop, 'market': market, 'threshold_pct': thresholdPct});
  /// Periodically (app open / 15-30 min) call korun; alerts_count > 0 hole notification dekhan.
  Future<Map<String, dynamic>> farmerAlerts(String farmerId) => _getM('/alerts/farmer/$farmerId');

  Future<Map<String, dynamic>> lossAssess({
    required String crop,
    required double distanceKm,
    double hoursSinceHarvest = 0,
    double? temperatureC,
    String? district,
    double? hoursToDeadline,
  }) =>
      _postM('/loss/assess', {
        'crop': crop,
        'distance_km': distanceKm,
        'hours_since_harvest': hoursSinceHarvest,
        if (temperatureC != null) 'temperature_c': temperatureC,
        if (district != null) 'district': district,
        if (hoursToDeadline != null) 'hours_to_deadline': hoursToDeadline,
      });

  Future<Map<String, dynamic>> weather({String district = 'Dhaka'}) => _getM('/weather', {'district': district});
  Future<List<dynamic>> demandRadar({String? crop}) => _getL('/demand-radar', {'crop': crop});

  /// speech_to_text-er text ekhane dien; response['reply'] text_to_speech-e shonan.
  Future<Map<String, dynamic>> chat(String text, {String market = 'Dhaka', double? quantityKg, String grade = 'B'}) =>
      _postM('/assistant/chat', {
        'text': text,
        'market': market,
        if (quantityKg != null) 'quantity_kg': quantityKg,
        'grade': grade,
      });

  void close() => _client.close();
}
