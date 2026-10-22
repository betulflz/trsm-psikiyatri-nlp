// Expo, EXPO_PUBLIC_* değişkenlerini derleme zamanında process.env üzerinden satır içine alır.
declare const process: { env: Record<string, string | undefined> };
