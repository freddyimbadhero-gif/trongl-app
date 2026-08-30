import React, { useEffect, useState } from "react";

import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import MapView, {
  Marker,
  Polyline,
} from "react-native-maps";

import * as Location from "expo-location";


export default function App() {
  const [location, setLocation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [routes, setRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);

  useEffect(() => {
    loadLocation();
  }, []);


  async function loadLocation() {
    try {
      const { status } =
        await Location.requestForegroundPermissionsAsync();

      if (status !== "granted") {
        Alert.alert(
          "Poloha není povolena",
          "TRONGL potřebuje přístup k poloze."
        );

        setLoading(false);
        return;
      }

      const current =
        await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.High,
        });

      setLocation({
        latitude: current.coords.latitude,
        longitude: current.coords.longitude,
      });

    } catch (error) {
      Alert.alert(
        "Chyba GPS",
        "Nepodařilo se získat tvoji polohu."
      );
    } finally {
      setLoading(false);
    }
  }


  function createTestRoutes() {
    if (!location) {
      return;
    }

    const start = location;

    const safeRoute = [
      start,

      {
        latitude: start.latitude + 0.0015,
        longitude: start.longitude + 0.0005,
      },

      {
        latitude: start.latitude + 0.003,
        longitude: start.longitude + 0.001,
      },

      {
        latitude: start.latitude + 0.0045,
        longitude: start.longitude + 0.002,
      },
    ];


    const fastRoute = [
      start,

      {
        latitude: start.latitude + 0.002,
        longitude: start.longitude + 0.0015,
      },

      {
        latitude: start.latitude + 0.0045,
        longitude: start.longitude + 0.002,
      },
    ];


    const generatedRoutes = [
      {
        id: "safe",
        name: "Nejbezpečnější",
        duration: 18,
        distance: 1.4,
        safety: 94,
        path: safeRoute,
      },

      {
        id: "fast",
        name: "Nejrychlejší",
        duration: 14,
        distance: 1.1,
        safety: 76,
        path: fastRoute,
      },
    ];


    setRoutes(generatedRoutes);
    setSelectedRoute(generatedRoutes[0]);
  }


  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator
          size="large"
          color="#00D084"
        />

        <Text style={styles.loadingText}>
          TRONGL získává tvoji polohu…
        </Text>
      </View>
    );
  }


  if (!location) {
    return (
      <View style={styles.loading}>
        <Text style={styles.errorTitle}>
          TRONGL nemá tvoji polohu
        </Text>

        <TouchableOpacity
          style={styles.primaryButton}
          onPress={loadLocation}
        >
          <Text style={styles.primaryButtonText}>
            Zkusit znovu
          </Text>
        </TouchableOpacity>
      </View>
    );
  }


  return (
    <View style={styles.container}>

      <MapView
        style={styles.map}
        showsUserLocation
        showsMyLocationButton
        initialRegion={{
          latitude: location.latitude,
          longitude: location.longitude,
          latitudeDelta: 0.015,
          longitudeDelta: 0.015,
        }}
      >

        <Marker
          coordinate={location}
          title="Tvoje poloha"
        />


        {selectedRoute && (
          <Polyline
            coordinates={selectedRoute.path}
            strokeColor="#00D084"
            strokeWidth={6}
          />
        )}

      </MapView>


      <View style={styles.topCard}>

        <Text style={styles.logo}>
          TRONGL
        </Text>

        <Text style={styles.subtitle}>
          Bezpečnější cesta městem
        </Text>

        <TouchableOpacity
          style={styles.primaryButton}
          onPress={createTestRoutes}
        >
          <Text style={styles.primaryButtonText}>
            🛡️ Najít bezpečnou trasu
          </Text>
        </TouchableOpacity>

      </View>


      {selectedRoute && (
        <View style={styles.bottomCard}>

          <Text style={styles.routeName}>
            {selectedRoute.name}
          </Text>

          <View style={styles.infoRow}>

            <View>
              <Text style={styles.label}>
                Čas
              </Text>

              <Text style={styles.value}>
                {selectedRoute.duration} min
              </Text>
            </View>


            <View>
              <Text style={styles.label}>
                Vzdálenost
              </Text>

              <Text style={styles.value}>
                {selectedRoute.distance} km
              </Text>
            </View>


            <View>
              <Text style={styles.label}>
                Bezpečnost
              </Text>

              <Text style={styles.safety}>
                {selectedRoute.safety}/100
              </Text>
            </View>

          </View>


          <View style={styles.routeButtons}>

            {routes.map((route) => (

              <TouchableOpacity
                key={route.id}
                style={[
                  styles.routeButton,
                  selectedRoute.id === route.id &&
                    styles.routeButtonActive,
                ]}
                onPress={() =>
                  setSelectedRoute(route)
                }
              >

                <Text style={styles.routeButtonText}>
                  {route.name}
                </Text>

              </TouchableOpacity>

            ))}

          </View>

        </View>
      )}

    </View>
  );
}


const styles = StyleSheet.create({

  container: {
    flex: 1,
  },

  map: {
    width: "100%",
    height: "100%",
  },

  loading: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 30,
  },

  loadingText: {
    marginTop: 15,
    fontSize: 16,
  },

  errorTitle: {
    fontSize: 18,
    fontWeight: "bold",
    marginBottom: 20,
  },

  topCard: {
    position: "absolute",
    top: 55,
    left: 20,
    right: 20,
    backgroundColor: "white",
    padding: 18,
    borderRadius: 16,
    elevation: 8,
  },

  logo: {
    fontSize: 25,
    fontWeight: "900",
  },

  subtitle: {
    marginTop: 3,
    marginBottom: 14,
    color: "#64748B",
  },

  primaryButton: {
    backgroundColor: "#1E293B",
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
  },

  primaryButtonText: {
    color: "white",
    fontWeight: "bold",
    fontSize: 15,
  },

  bottomCard: {
    position: "absolute",
    bottom: 25,
    left: 15,
    right: 15,
    backgroundColor: "white",
    padding: 20,
    borderRadius: 18,
    elevation: 10,
  },

  routeName: {
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 15,
  },

  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  label: {
    fontSize: 12,
    color: "#64748B",
  },

  value: {
    fontSize: 16,
    fontWeight: "bold",
    marginTop: 3,
  },

  safety: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#00A86B",
    marginTop: 3,
  },

  routeButtons: {
    flexDirection: "row",
    gap: 8,
    marginTop: 18,
  },

  routeButton: {
    flex: 1,
    padding: 11,
    borderRadius: 9,
    backgroundColor: "#F1F5F9",
    alignItems: "center",
  },

  routeButtonActive: {
    backgroundColor: "#D1FAE5",
    borderWidth: 1,
    borderColor: "#00D084",
  },

  routeButtonText: {
    fontSize: 12,
    fontWeight: "bold",
  },

});
