jest.mock('react-native-worklets', () => require('react-native-worklets/src/mock'));
// Reanimated 4.7 initializes native CSS callbacks when its Jest mock is imported.
jest.mock('react-native-reanimated/src/initializers', () => ({
  initializeReanimatedModule: jest.fn(),
}));
jest.mock('react-native-reanimated', () => ({
  ...require('react-native-reanimated/mock'),
  useReducedMotion: () => false,
}));
