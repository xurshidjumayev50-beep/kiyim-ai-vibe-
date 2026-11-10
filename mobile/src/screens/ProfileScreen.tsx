import React from 'react';
import { View, Text, SafeAreaView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export const ProfileScreen: React.FC = () => {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#000' }}>
      <View style={{ flex: 1, padding: 18 }}>
        <Text style={{ color: '#fff', fontSize: 24, fontWeight: '900', marginBottom: 16 }}>Shaxsiy Profil</Text>

        <View style={{ backgroundColor: '#18181b', borderRadius: 24, padding: 18, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#27272a', marginBottom: 20 }}>
          <View style={{ width: 60, height: 60, borderRadius: 30, backgroundColor: '#4f46e5', justifyContent: 'center', alignItems: 'center', marginRight: 16 }}>
            <Ionicons name="person" size={28} color="#fff" />
          </View>
          <View>
            <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>Xurshid</Text>
            <Text style={{ color: '#818cf8', fontSize: 12, marginTop: 2 }}>Kiyim AI Premium</Text>
          </View>
        </View>

        <View style={{ backgroundColor: '#18181b', borderRadius: 20, padding: 16, borderWidth: 1, borderColor: '#27272a' }}>
          <Text style={{ color: '#a1a1aa', fontSize: 12, fontWeight: 'bold', textTransform: 'uppercase', marginBottom: 12 }}>
            Tana Parametrlari (Standart)
          </Text>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#27272a' }}>
            <Text style={{ color: '#d4d4d8', fontSize: 13 }}>Bo'y:</Text>
            <Text style={{ color: '#fff', fontSize: 13, fontWeight: 'bold' }}>178 sm</Text>
          </View>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#27272a' }}>
            <Text style={{ color: '#d4d4d8', fontSize: 13 }}>Vazn:</Text>
            <Text style={{ color: '#fff', fontSize: 13, fontWeight: 'bold' }}>72 kg</Text>
          </View>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8 }}>
            <Text style={{ color: '#d4d4d8', fontSize: 13 }}>Tavsiya o'lchami:</Text>
            <Text style={{ color: '#10b981', fontSize: 13, fontWeight: 'bold' }}>M</Text>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
};
