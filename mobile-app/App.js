import React from 'react';
import { Provider } from 'react-redux';
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import store from './src/store/store';
import AppNavigator from './src/navigation/AppNavigator';
import { ThemeProvider } from './src/store/ThemeContext';

export default function App() {
  return (
    <Provider store={store}>
      <ThemeProvider>
        <GestureHandlerRootView style={{ flex: 1 }}>
          <NavigationContainer>
            <AppNavigator />
            <StatusBar style="auto" />
          </NavigationContainer>
        </GestureHandlerRootView>
      </ThemeProvider>
    </Provider>
  );
}
