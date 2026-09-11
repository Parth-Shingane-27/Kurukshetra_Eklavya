import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Text } from "react-native";
import { CitizenProvider } from "../context/CitizenContext";
import ExploreScreen from "../screens/ExploreScreen";
import HomeScreen from "../screens/HomeScreen";
import { colors } from "../theme";

const Tab = createBottomTabNavigator();

function TabIcon({ symbol, color }) {
  return <Text style={{ fontSize: 18, color }}>{symbol}</Text>;
}

export default function MainTabs() {
  return (
    <CitizenProvider>
      <Tab.Navigator
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: colors.accent,
          tabBarInactiveTintColor: colors.textMuted,
          tabBarStyle: { borderTopColor: colors.border },
        }}
      >
        <Tab.Screen name="Home" component={HomeScreen} options={{ tabBarIcon: ({ color }) => <TabIcon symbol="🏠" color={color} /> }} />
        <Tab.Screen name="Explore" component={ExploreScreen} options={{ tabBarIcon: ({ color }) => <TabIcon symbol="🔍" color={color} /> }} />
      </Tab.Navigator>
    </CitizenProvider>
  );
}
