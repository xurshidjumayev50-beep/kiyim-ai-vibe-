import React from 'react';
import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface FitScoreGaugeProps {
  fitStatus: string;
  matchPercentage: number;
  recommendedSize: string;
  fitAdvice: string;
}

export const FitScoreGauge: React.FC<FitScoreGaugeProps> = ({
  fitStatus,
  matchPercentage,
  recommendedSize,
  fitAdvice,
}) => {
  const isPerfect = fitStatus === 'perfect';
  const isTight = fitStatus === 'tight';
  
  const statusColor = isPerfect ? '#10b981' : isTight ? '#f43f5e' : '#f59e0b';
  const statusLabel = isPerfect ? 'Ideal Moslik' : isTight ? 'Biroz Tor' : 'Katta / Oversized';

  return (
    <View style={{ backgroundColor: '#18181b', borderRadius: 24, padding: 16, marginTop: 16, borderWidth: 1, borderColor: '#27272a' }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="body-outline" size={20} color="#818cf8" style={{ marginRight: 6 }} />
          <Text style={{ color: '#fff', fontWeight: 'bold', fontSize: 14 }}>O'lcham va Moslik Tahlili</Text>
        </View>
        <View style={{ backgroundColor: `${statusColor}25`, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, borderWidth: 1, borderColor: `${statusColor}50` }}>
          <Text style={{ color: statusColor, fontSize: 11, fontWeight: 'bold' }}>{statusLabel}</Text>
        </View>
      </View>

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 6 }}>
        <Text style={{ color: '#a1a1aa', fontSize: 12 }}>AI Moslik foizi:</Text>
        <Text style={{ color: '#fff', fontSize: 20, fontWeight: '900' }}>{matchPercentage}%</Text>
      </View>

      <View style={{ height: 8, backgroundColor: '#27272a', borderRadius: 4, overflow: 'hidden', marginBottom: 12 }}>
        <View style={{ height: '100%', width: `${matchPercentage}%`, backgroundColor: statusColor, borderRadius: 4 }} />
      </View>

      <View style={{ backgroundColor: '#09090b', borderRadius: 16, padding: 12, borderWidth: 1, borderColor: '#27272a' }}>
        <Text style={{ color: '#d4d4d8', fontSize: 12, lineHeight: 18 }}>{fitAdvice}</Text>
        <Text style={{ color: '#818cf8', fontSize: 12, fontWeight: 'bold', marginTop: 4 }}>
          Tavsiya etilgan o'lcham: {recommendedSize}
        </Text>
      </View>
    </View>
  );
};
