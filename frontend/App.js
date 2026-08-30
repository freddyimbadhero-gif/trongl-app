import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Alert, ActivityIndicator, Modal } from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';
import * as Location from 'expo-location';

const API_BASE_URL = 'http://localhost:8000';

export default function App() {
  const [location, setLocation] = useState(null);
  const [routes, setRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Stavy pro AI Asistenta
  const [assistantAdvice, setAssistantAdvice] = useState('');
  const [modalVisible, setModalVisible] = useState(false);

  useEffect(() => {
    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Chyba', 'Aplikace vyžaduje přístup k poloze pro bezpečnou navigaci.');
        setLoading(false);
        return;
      }

      let currentLocation = await Location.getCurrentPositionAsync({});
      setLocation({
        lat: currentLocation.coords.latitude,
        lng: currentLocation.coords.longitude,
      });
      setLoading(false);
    })();
  }, []);

  const fetchRoutes = async () => {
    if (!location) return;
    setLoading(true);

    try {
      const destination = { lat: location.lat + 0.008, lng: location.lng + 0.008 };
      const response = await fetch(`${API_BASE_URL}/api/v1/navigation/routes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin: location,
          destination: destination,
          is_night: new Date().getHours() >= 22 || new Date().getHours() < 6
        })
      });

      const data = await response.json();
      setRoutes(data.routes);
      if (data.routes.length > 0) setSelectedRoute(data.routes[0]);
    } catch (error) {
      Alert.alert('Chyba připojení', 'Nelze načíst trasy z backendu TRONGL.');
    } finally {
      setLoading(false);
    }
  };

  // Volání AI Bezpečnostního asistenta
  const askAIAssistant = async () => {
    if (!selectedRoute) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/assistant/advise`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          is_night: new Date().getHours() >= 22 || new Date().getHours() < 6,
          incident_types: ["lighting_issue"],
          safety_score: selectedRoute.safety_score
        })
      });

      const data = await response.json();
      setAssistantAdvice(data.advice);
      setModalVisible(true);
    } catch (err) {
      Alert.alert('Chyba', 'AI Asistent je momentálně nedostupný.');
    }
  };

  if (loading || !location) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#00D084" />
        <Text style={{ marginTop: 10 }}>Načítání TRONGL bezpečnostní mapy...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        initialRegion={{
          latitude: location.lat,
          longitude: location.lng,
          latitudeDelta: 0.015,
          longitudeDelta: 0.015,
        }}
      >
        <Marker coordinate={{ latitude: location.lat, longitude: location.lng }} title="Moje poloha" />
        {selectedRoute && (
          <Polyline
            coordinates={selectedRoute.path.map(p => ({ latitude: p.lat, longitude: p.lng }))}
            strokeColor={selectedRoute.route_id === 'route_safest' ? '#00D084' : '#FF4D4D'}
            strokeWidth={5}
          />
        )}
      </MapView>

      <View style={styles.topCard}>
        <Text style={styles.cardTitle}>Kam to bude?</Text>
        <TouchableOpacity style={styles.searchButton} onPress={fetchRoutes}>
          <Text style={styles.searchButtonText}>🔍 Spočítat bezpečné trasy</Text>
        </TouchableOpacity>
      </View>

      {selectedRoute && (
        <View style={styles.bottomCard}>
          <Text style={styles.routeTitle}>{selectedRoute.title}</Text>
          <Text style={styles.routeScore}>
            Skóre bezpečnosti: <Text style={{ fontWeight: 'bold', color: '#00D084' }}>{selectedRoute.safety_score}/100</Text>
          </Text>
          
          <TouchableOpacity style={styles.aiButton} onPress={askAIAssistant}>
            <Text style={styles.aiButtonText}>🤖 Zeptat se AI Asistenta na rizika</Text>
          </TouchableOpacity>

          <View style={styles.buttonRow}>
            {routes.map((r) => (
              <TouchableOpacity
                key={r.route_id}
                style={[styles.chipButton, selectedRoute.route_id === r.route_id && styles.chipActive]}
                onPress={() => setSelectedRoute(r)}
              >
                <Text style={styles.chipText}>{r.title} ({r.duration_minutes} min)</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {/* POPUP OKNO AI ASISTENTA */}
      <Modal visible={modalVisible} transparent={true} animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>🤖 AI Bezpečnostní Asistent</Text>
            <Text style={styles.modalText}>{assistantAdvice}</Text>
            <TouchableOpacity style={styles.closeButton} onPress={() => setModalVisible(false)}>
              <Text style={styles.closeButtonText}>Rozumím</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  map: { width: '100%', height: '100%' },
  topCard: { position: 'absolute', top: 50, left: 20, right: 20, backgroundColor: 'white', padding: 15, borderRadius: 12, elevation: 5 },
  cardTitle: { fontSize: 16, fontWeight: 'bold', marginBottom: 8 },
  searchButton: { backgroundColor: '#1E293B', padding: 12, borderRadius: 8, alignItems: 'center' },
  searchButtonText: { color: 'white', fontWeight: 'bold' },
  bottomCard: { position: 'absolute', bottom: 30, left: 20, right: 20, backgroundColor: 'white', padding: 20, borderRadius: 16, elevation: 8 },
  routeTitle: { fontSize: 18, fontWeight: 'bold' },
  routeScore: { fontSize: 14, marginVertical: 4 },
  aiButton: { backgroundColor: '#F0FDFA', padding: 10, borderRadius: 8, marginVertical: 8, borderWidth: 1, borderColor: '#99F6E4' },
  aiButtonText: { color: '#0D9488', fontWeight: 'bold', textAlign: 'center', fontSize: 12 },
  buttonRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  chipButton: { padding: 10, borderRadius: 8, backgroundColor: '#F1F5F9', flex: 0.48, alignItems: 'center' },
  chipActive: { backgroundColor: '#E2E8F0', borderWidth: 1, borderColor: '#00D084' },
  chipText: { fontSize: 12, fontWeight: 'bold' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center' },
  modalContent: { width: '85%', backgroundColor: 'white', padding: 20, borderRadius: 16, alignItems: 'center' },
  modalTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 12 },
  modalText: { fontSize: 14, color: '#334155', textAlign: 'center', marginBottom: 20, lineHeight: 20 },
  closeButton: { backgroundColor: '#1E293B', paddingVertical: 10, paddingHorizontal: 24, borderRadius: 8 },
  closeButtonText: { color: 'white', fontWeight: 'bold' }
});
