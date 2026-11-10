import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Image,
  ScrollView,
  ActivityIndicator,
  Alert,
  SafeAreaView,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import { getGarments, performTryOn, API_BASE_URL } from '../services/api';
import { FitScoreGauge } from '../components/FitScoreGauge';

export const TryOnScreen: React.FC = () => {
  const [userImageUri, setUserImageUri] = useState<string | null>(null);
  const [selectedGarment, setSelectedGarment] = useState<any>(null);
  const [garments, setGarments] = useState<any[]>([]);
  const [selectedSize, setSelectedSize] = useState('M');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    loadGarments();
  }, []);

  const loadGarments = async () => {
    try {
      const data = await getGarments();
      setGarments(data);
      if (data.length > 0) {
        setSelectedGarment(data[0]);
      }
    } catch (err) {
      console.log('Garments loading failed:', err);
    }
  };

  const pickImage = async (useCamera = false) => {
    const perm = useCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (!perm.granted) {
      Alert.alert('Ruxsat kerak', 'Suratga olish yoki galereyadan rasm tanlash uchun ruxsat bering.');
      return;
    }

    const res = useCamera
      ? await ImagePicker.launchCameraAsync({ allowsEditing: true, aspect: [3, 4], quality: 0.8 })
      : await ImagePicker.launchImageLibraryAsync({ allowsEditing: true, aspect: [3, 4], quality: 0.8 });

    if (!res.canceled && res.assets[0].uri) {
      setUserImageUri(res.assets[0].uri);
    }
  };

  const handleTryOn = async () => {
    if (!userImageUri) {
      Alert.alert('Rasm tanlanmadi', 'Iltimos, o\'z rasmingizni yuklang yoki rasmga oling.');
      return;
    }

    if (!selectedGarment) {
      Alert.alert('Kiyim tanlanmadi', 'Katalogdan kiyimni tanlang.');
      return;
    }

    try {
      setLoading(true);
      setResult(null);

      const res = await performTryOn(userImageUri, selectedGarment.image_url, selectedSize);
      if (res.success) {
        setResult(res);
      } else {
        Alert.alert('Xatolik', res.error || 'Generatsiya qilib bo\'lmadi');
      }
    } catch (err: any) {
      Alert.alert('Xatolik', err.message || 'Serverga ulanishda xatolik');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#000' }}>
      <ScrollView contentContainerStyle={{ padding: 18 }}>
        {/* Header */}
        <View style={{ marginBottom: 16 }}>
          <Text style={{ color: '#fff', fontSize: 26, fontWeight: '900' }}>Kiyim AI Studio</Text>
          <Text style={{ color: '#a1a1aa', fontSize: 13, marginTop: 4 }}>
            Virtual kiyib ko'rish & tana o'lchami tahlili
          </Text>
        </View>

        {/* User image and selected garment cards */}
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 }}>
          {/* User photo */}
          <View style={{ width: '48%', backgroundColor: '#18181b', borderRadius: 20, padding: 12, borderWidth: 1, borderColor: '#27272a' }}>
            <Text style={{ color: '#a1a1aa', fontSize: 10, fontWeight: 'bold', textTransform: 'uppercase', marginBottom: 8 }}>
              Sizning Rasmingiz
            </Text>
            <View style={{ height: 160, backgroundColor: '#09090b', borderRadius: 14, overflow: 'hidden', justifyContent: 'center', alignItems: 'center' }}>
              {userImageUri ? (
                <Image source={{ uri: userImageUri }} style={{ width: '100%', height: '100%' }} resizeMode="cover" />
              ) : (
                <Ionicons name="person-outline" size={36} color="#52525b" />
              )}
            </View>
            <View style={{ flexDirection: 'row', justifyContent: 'space-around', marginTop: 10 }}>
              <TouchableOpacity onPress={() => pickImage(true)} style={{ padding: 6 }}>
                <Ionicons name="camera" size={20} color="#818cf8" />
              </TouchableOpacity>
              <TouchableOpacity onPress={() => pickImage(false)} style={{ padding: 6 }}>
                <Ionicons name="images" size={20} color="#818cf8" />
              </TouchableOpacity>
            </View>
          </View>

          {/* Garment photo */}
          <View style={{ width: '48%', backgroundColor: '#18181b', borderRadius: 20, padding: 12, borderWidth: 1, borderColor: '#27272a' }}>
            <Text style={{ color: '#a1a1aa', fontSize: 10, fontWeight: 'bold', textTransform: 'uppercase', marginBottom: 8 }}>
              Tanlangan Kiyim
            </Text>
            <View style={{ height: 160, backgroundColor: '#09090b', borderRadius: 14, overflow: 'hidden', justifyContent: 'center', alignItems: 'center', padding: 8 }}>
              {selectedGarment ? (
                <Image
                  source={{ uri: selectedGarment.image_url.startsWith('http') ? selectedGarment.image_url : `${API_BASE_URL}${selectedGarment.image_url}` }}
                  style={{ width: '100%', height: '100%' }}
                  resizeMode="contain"
                />
              ) : (
                <Ionicons name="shirt-outline" size={36} color="#52525b" />
              )}
            </View>
            <Text style={{ color: '#d4d4d8', fontSize: 11, textAlign: 'center', marginTop: 8 }} numberOfLines={1}>
              {selectedGarment ? selectedGarment.title : 'Kiyim tanlang'}
            </Text>
          </View>
        </View>

        {/* Size Selection */}
        <Text style={{ color: '#d4d4d8', fontSize: 12, fontWeight: 'bold', marginBottom: 8 }}>O'lcham (Size):</Text>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 18 }}>
          {['XS', 'S', 'M', 'L', 'XL', 'XXL'].map((sz) => (
            <TouchableOpacity
              key={sz}
              onPress={() => setSelectedSize(sz)}
              style={{
                width: 48,
                height: 44,
                borderRadius: 12,
                justifyContent: 'center',
                alignItems: 'center',
                backgroundColor: selectedSize === sz ? '#4f46e5' : '#18181b',
                borderWidth: 1,
                borderColor: selectedSize === sz ? '#818cf8' : '#27272a',
              }}
            >
              <Text style={{ color: selectedSize === sz ? '#fff' : '#a1a1aa', fontWeight: 'bold', fontSize: 12 }}>
                {sz}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Try-On Button */}
        <TouchableOpacity
          onPress={handleTryOn}
          disabled={loading}
          style={{
            backgroundColor: loading ? '#312e81' : '#4f46e5',
            height: 54,
            borderRadius: 18,
            flexDirection: 'row',
            justifyContent: 'center',
            alignItems: 'center',
            shadowColor: '#4f46e5',
            shadowOpacity: 0.4,
            shadowRadius: 10,
          }}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="sparkles" size={18} color="#fff" style={{ marginRight: 8 }} />
              <Text style={{ color: '#fff', fontWeight: 'bold', fontSize: 15 }}>Virtual Kiyib Ko'rish (Try-On)</Text>
            </>
          )}
        </TouchableOpacity>

        {/* Result & Fit Score */}
        {result && (
          <View style={{ marginTop: 24 }}>
            <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold', marginBottom: 10 }}>AI Natijasi:</Text>
            <View style={{ height: 360, borderRadius: 24, overflow: 'hidden', borderWidth: 1, borderColor: '#27272a', backgroundColor: '#09090b' }}>
              <Image
                source={{ uri: result.result_image_url.startsWith('http') ? result.result_image_url : `${API_BASE_URL}${result.result_image_url}` }}
                style={{ width: '100%', height: '100%' }}
                resizeMode="cover"
              />
            </View>

            <FitScoreGauge
              fitStatus={result.fit_status}
              matchPercentage={result.match_percentage}
              recommendedSize={result.recommended_size}
              fitAdvice={result.fit_advice}
            />
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};
