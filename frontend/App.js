import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';
import * as Location from 'expo-location';

const API_BASE_URL = 'http://localhost:8000';

export default function App() {
  const [location, setLocation] = useState(null);
  const [routes, setRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Chyba', 'Aplikace vyžaduje přístup k poloze pro bezpečnou navigaci.');
        setLoading(false);
        return;
      }

      let currentLocation = await Location.getCurrentPositionAsync({});
      const coords = {
        lat: currentLocation.coords.latitude,
        lng: currentLocation.coords.longitude,
      };
      setLocation(coords);
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

  const reportIncident = async (category) => {
    if (!location) return;
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/incidents?category=${category}&lat=${location.lat}&lng=${location.lng}`,
        { method: 'POST' }
      );
      if (response.ok) {
        Alert.alert('🛡️ Nahlášeno', 'Děkujeme. Vaše hlášení pomůže ostatním chodcům.');
      }
    } catch (err) {
      Alert.alert('Chyba', 'Odeslání hlášení se nepodařilo.');
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
          <Text style={styles.routeReason}>{selectedRoute.summary_reason}</Text>

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

          <TouchableOpacity 
            style={styles.reportButton} 
            onPress={() => reportIncident('lighting_issue')}
          >
            <Text style={styles.reportButtonText}>⚠️ Nahlásit neosvětlené/nebezpečné místo</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  map: { width: '100%', height: '100%' },
  topCard: {
    position: 'absolute',
    top: 50,
    left: 20,
    right: 20,
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 12,
    elevation: 5,
  },
  cardTitle: { fontSize: 16, fontWeight: 'bold', marginBottom: 8 },
  searchButton: { backgroundColor: '#1E293B', padding: 12, borderRadius: 8, alignItems: 'center' },
  searchButtonText: { color: 'white', fontWeight: 'bold' },
  bottomCard: {
    position: 'absolute',
    bottom: 30,
    left: 20,
    right: 20,
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 16,
    elevation: 8,
  },
  routeTitle: { fontSize: 18, fontWeight: 'bold' },
  routeScore: { fontSize: 14, marginVertical: 4 },
  routeReason: { fontSize: 12, color: '#64748B', marginBottom: 12 },
  buttonRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  chipButton: { padding: 10, borderRadius: 8, backgroundColor: '#F1F5F9', flex: 0.48, alignItems: 'center' },
  chipActive: { backgroundColor: '#E2E8F0', borderWidth: 1, borderColor: '#00D084' },
  chipText: { fontSize: 12, fontWeight: 'bold' },
  reportButton: { backgroundColor: '#FFF1F2', padding: 12, borderRadius: 8, alignItems: 'center', borderWidth: 1, borderColor: '#FECDD3' },
  reportButtonText: { color: '#E11D48', fontWeight: 'bold', fontSize: 12 },
});
