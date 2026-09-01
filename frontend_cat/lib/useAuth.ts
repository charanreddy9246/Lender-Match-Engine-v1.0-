"use client";

// Tracks whether an admin is logged in (via Firebase) and provides a way to
// get their current login token for calling the admin API. Every admin page
// uses this to decide "show the page" vs "send back to login."

import { onAuthStateChanged, signInWithEmailAndPassword, signOut, type User } from "firebase/auth";
import { useEffect, useState } from "react";

import { auth } from "./firebase";

export function useAuth() {
  const [user, setUser] = useState<User | null | undefined>(undefined); // undefined = still checking
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return onAuthStateChanged(auth, (u) => setUser(u));
  }, []);

  async function login(email: string, password: string) {
    setError(null);
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch {
      setError("Wrong email or password.");
    }
  }

  async function logout() {
    await signOut(auth);
  }

  async function getToken(): Promise<string | null> {
    if (!auth.currentUser) return null;
    return auth.currentUser.getIdToken();
  }

  return { user, loading: user === undefined, error, login, logout, getToken };
}
