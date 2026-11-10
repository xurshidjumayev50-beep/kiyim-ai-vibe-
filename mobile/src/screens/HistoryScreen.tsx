import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  Image,
  TouchableOpacity,
  Alert,
  SafeAreaView,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { getHistory, deleteHistoryItem, clearAllHistory, API_BASE_URL } from '../services/api';

export const HistoryScreen: React.FC = () => {
  const [history, setHistory] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const fetchHistory = async () => {
    setRefreshing(true);
    try {
      const data = await getHistory();
      setHistory(data);
    } catch (err) {
      console.log('Tarixni yuklashda xatolik:', err);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDelete = (id: number) => {
    Alert.alert('O\'chirish', 'Ushbu natijani tarixdan o\'chirasizmi?', [
      { text: 'Bekor qilish', style: 'cancel' },
      {
        text: 'O\'chirish',
        style: 'destructive',
        onPress: async () => {
          await deleteHistoryItem(id);
          setHistory((prev) => prev.filter((item) => item.id !== id));
        },
      },
    ]);
  };

  const handleClearAll = () => {
    Alert.alert('Tozalash', 'Barcha kiyish tarixi o\'chiriladi. Rozimisiz?', [
      { text: 'Bekor qilish', style: 'cancel' },
      {
        text: 'Hammasini tozalash',
        style: 'destructive',
        onPress: async () => {
          await clearAllHistory();
          setHistory([]);
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#000' }}>
      <View style={{ flex: 1, padding: 18 }}>
        {/* Header */}
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <View>
            <Text style={{ color: '#fff', fontSize: 24, fontWeight: '900' }}>Kiyish Tarixi</Text>
            <Text style={{ color: '#a1a1aa', fontSize: 12 }}>{history.length} ta natija</Text>
          </View>
          {history.length > 0 && (
            <TouchableOpacity
              onPress={handleClearAll}
              style={{ backgroundColor: '#ef444420', borderWidth: 1, borderColor: '#ef444440', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 }}
            >
              <Text style={{ color: '#ef4444', fontSize: 11, fontWeight: 'bold' }}>Tozalash</Text>
            </TouchableOpacity>
          )}
        </View>

        <FlatList
          data={history}
          keyExtractor={(item) => item.id.toString()}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={fetchHistory} tintColor="#818cf8" />}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={
            <View style={{ alignItems: 'center', justifyContent: 'center', paddingVertical: 80 }}>
              <Ionicons name="shirt-outline" size={48} color="#3f3f46" />
              <Text style={{ color: '#71717a', fontSize: 13, marginTop: 8 }}>Tarix bo'sh</Text>
            </View>
          }
          renderItem={({ item }) => (
            <View style={{ backgroundColor: '#18181b', borderRadius: 20, padding: 12, marginBottom: 12, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#27272a' }}>
              <Image
                source={{ uri: item.result_image_url.startsWith('http') ? item.result_image_url : `${API_BASE_URL}${item.result_image_url}` }}
                style={{ width: 70, height: 90, borderRadius: 12, backgroundColor: '#09090b' }}
                resizeMode="cover"
              />
              <View style={{ flex: 1, marginLeft: 12, justifyContent: 'space-between' }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text style={{ color: '#fff', fontWeight: 'bold', fontSize: 14 }}>
                    {item.fit_status === 'perfect' ? 'Ideal Moslik' : item.fit_status === 'tight' ? 'Tor' : 'Katta'}
                  </Text>
                  <TouchableOpacity onPress={() => handleDelete(item.id)} style={{ padding: 4 }}>
                    <Ionicons name="close" size={18} color="#71717a" />
                  </TouchableOpacity>
                </View>
                <Text style={{ color: '#818cf8', fontSize: 12, fontWeight: 'bold' }}>Moslik: {item.match_percentage}%</Text>
                <Text style={{ color: '#a1a1aa', fontSize: 11, marginTop: 2 }} numberOfLines={1}>{item.fit_advice}</Text>
                <Text style={{ color: '#52525b', fontSize: 9, marginTop: 4 }}>{new Date(item.created_at).toLocaleDateString()}</Text>
              </View>
            </View>
          )}
        />
      </View>
    </SafeAreaView>
  );
};
