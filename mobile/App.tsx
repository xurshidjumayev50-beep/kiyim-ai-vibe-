import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

import { TryOnScreen } from './src/screens/TryOnScreen';
import { HistoryScreen } from './src/screens/HistoryScreen';
import { ProfileScreen } from './src/screens/ProfileScreen';

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarStyle: {
            backgroundColor: '#09090b',
            borderTopColor: '#27272a',
            height: 65,
            paddingBottom: 10,
            paddingTop: 8,
          },
          tabBarActiveTintColor: '#818cf8',
          tabBarInactiveTintColor: '#71717a',
          tabBarIcon: ({ focused, color, size }) => {
            let iconName: any = 'shirt';
            if (route.name === 'Studio') {
              iconName = focused ? 'sparkles' : 'sparkles-outline';
            } else if (route.name === 'History') {
              iconName = focused ? 'time' : 'time-outline';
            } else if (route.name === 'Profile') {
              iconName = focused ? 'person' : 'person-outline';
            }
            return <Ionicons name={iconName} size={22} color={color} />;
          },
        })}
      >
        <Tab.Screen name="Studio" component={TryOnScreen} options={{ tabBarLabel: 'Studio' }} />
        <Tab.Screen name="History" component={HistoryScreen} options={{ tabBarLabel: 'Tarix' }} />
        <Tab.Screen name="Profile" component={ProfileScreen} options={{ tabBarLabel: 'Profil' }} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
