import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { StatusBar } from "expo-status-bar";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import MainTabs from "./src/navigation/MainTabs";
import ApplicationWebViewScreen from "./src/screens/ApplicationWebViewScreen";
import BundleScreen from "./src/screens/BundleScreen";
import ChecklistScreen from "./src/screens/ChecklistScreen";
import EligibilityScreen from "./src/screens/EligibilityScreen";
import LandingScreen from "./src/screens/LandingScreen";
import OnboardingScreen from "./src/screens/OnboardingScreen";
import TraceScreen from "./src/screens/TraceScreen";
import { colors } from "./src/theme";

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <NavigationContainer>
          <StatusBar style="dark" />
          <Stack.Navigator
            initialRouteName="Landing"
            screenOptions={{
              headerTintColor: colors.accent,
              headerStyle: { backgroundColor: colors.surface },
              headerShadowVisible: false,
              contentStyle: { backgroundColor: colors.bg },
            }}
          >
            <Stack.Screen name="Landing" component={LandingScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Onboarding" component={OnboardingScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Main" component={MainTabs} options={{ headerShown: false }} />
            <Stack.Screen name="Eligibility" component={EligibilityScreen} options={{ title: "Eligible schemes" }} />
            <Stack.Screen name="Bundle" component={BundleScreen} options={{ title: "Optimized bundle" }} />
            <Stack.Screen name="Checklist" component={ChecklistScreen} options={{ title: "Checklist" }} />
            <Stack.Screen name="Trace" component={TraceScreen} options={{ title: "Reasoning trace" }} />
            <Stack.Screen
              name="ApplicationWebView"
              component={ApplicationWebViewScreen}
              options={({ route }) => ({ title: route.params?.schemeName || "Application" })}
            />
          </Stack.Navigator>
        </NavigationContainer>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
