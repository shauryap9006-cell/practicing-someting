/**
 * RailTwin-X Firebase SDK Initialization
 * Provides Firebase Auth, Firestore, and Cloud Messaging (FCM) instances.
 */

import { initializeApp, getApps, getApp, FirebaseApp } from 'firebase/app';
import { getAuth, Auth } from 'firebase/auth';
import { getFirestore, Firestore } from 'firebase/firestore';

export const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'AIzaSyDFAojTqSzmcVL4Op151mQ8simCRqbczBo',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'farmer-4b216.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'farmer-4b216',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'farmer-4b216.firebasestorage.app',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '53760063223',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:53760063223:web:753dae066ee022e27205f2',
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || 'G-WQJ0V0BJC1',
};

// Initialize Firebase App as Singleton
export const app: FirebaseApp = !getApps().length ? initializeApp(firebaseConfig) : getApp();

// Firebase Services
export const auth: Auth = getAuth(app);
export const db: Firestore = getFirestore(app);

export default app;
