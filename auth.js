/**
 * PowerForecast — Supabase Authentication & Session Client
 * Integrates Supabase Auth for Signup, Login, Google OAuth, Forgot Password, and Route Guards.
 */

(function (window) {
    'use strict';

    const SUPABASE_CONFIG = {
        url: window.SUPABASE_URL || 'https://ysfruhloqnelyysdwvog.supabase.co',
        anonKey: window.SUPABASE_ANON_KEY || 'sb_publishable_GjVlGJjSHfWubSBswskS1A_gqTK6e_6'
    };

    let supabaseClient = null;

    /**
     * Initializes the Supabase client.
     */
    function getSupabase() {
        if (supabaseClient) return supabaseClient;

        if (window.supabase && typeof window.supabase.createClient === 'function') {
            supabaseClient = window.supabase.createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.anonKey, {
                auth: {
                    persistSession: true,
                    autoRefreshToken: true,
                    detectSessionInUrl: true,
                    storage: window.localStorage
                }
            });
            return supabaseClient;
        }

        console.error('Supabase library (@supabase/supabase-js) is not loaded on this page.');
        return null;
    }

    /**
     * Helper to retrieve cached user synchronously for immediate page guards.
     */
    function getCachedUser() {
        try {
            // Check Supabase v2 storage keys
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('sb-') && key.endsWith('-auth-token')) {
                    const data = JSON.parse(localStorage.getItem(key));
                    if (data && data.user) return data.user;
                }
            }
            // Fallback to legacy or custom cached user
            const raw = localStorage.getItem('powerforecast_user');
            if (raw) return JSON.parse(raw);
        } catch (e) {
            console.warn('Error reading cached user:', e);
        }
        return null;
    }

    function setCachedUser(user) {
        try {
            if (user) {
                localStorage.setItem('powerforecast_user', JSON.stringify({
                    id: user.id,
                    email: user.email,
                    name: user.user_metadata?.full_name || user.user_metadata?.name || user.email?.split('@')[0] || 'User',
                    avatar: user.user_metadata?.avatar_url || user.user_metadata?.picture || '',
                    provider: user.app_metadata?.provider || 'email'
                }));
            } else {
                localStorage.removeItem('powerforecast_user');
            }
        } catch (e) {}
    }

    const PowerForecastAuth = {
        config: SUPABASE_CONFIG,

        getClient: getSupabase,

        /**
         * Checks if a user is currently authenticated (synchronous quick check).
         */
        isAuthenticatedSync() {
            return getCachedUser() !== null;
        },

        /**
         * Asynchronously gets the current active session.
         */
        async getSession() {
            const client = getSupabase();
            if (!client) return null;
            try {
                const { data, error } = await client.auth.getSession();
                if (error) throw error;
                if (data?.session?.user) {
                    setCachedUser(data.session.user);
                }
                return data?.session || null;
            } catch (err) {
                console.warn('getSession error:', err);
                return null;
            }
        },

        /**
         * Asynchronously gets the current user object.
         */
        async getUser() {
            const client = getSupabase();
            if (!client) return getCachedUser();
            try {
                const { data, error } = await client.auth.getUser();
                if (error || !data?.user) return getCachedUser();
                setCachedUser(data.user);
                return data.user;
            } catch (err) {
                return getCachedUser();
            }
        },

        /**
         * Sign Up a new user with full name, email, and password.
         */
        async signUp(fullName, email, password) {
            const client = getSupabase();
            if (!client) throw new Error('Supabase client unavailable.');

            const cleanEmail = email.trim().toLowerCase();
            const { data, error } = await client.auth.signUp({
                email: cleanEmail,
                password: password,
                options: {
                    data: {
                        full_name: fullName.trim(),
                        name: fullName.trim()
                    },
                    emailRedirectTo: window.location.origin + '/login.html'
                }
            });

            if (error) throw error;

            if (data?.user) {
                setCachedUser(data.user);
            }

            return data;
        },

        /**
         * Sign in with Email and Password.
         */
        async signIn(email, password, rememberMe = true) {
            const client = getSupabase();
            if (!client) throw new Error('Supabase client unavailable.');

            const cleanEmail = email.trim().toLowerCase();
            const { data, error } = await client.auth.signInWithPassword({
                email: cleanEmail,
                password: password
            });

            if (error) throw error;

            if (data?.user) {
                setCachedUser(data.user);
            }

            return data;
        },

        /**
         * Sign in / Sign up via Google OAuth.
         */
        async signInWithGoogle() {
            const client = getSupabase();
            if (!client) throw new Error('Supabase client unavailable.');

            const redirectTo = window.location.origin + '/home.html';
            const { data, error } = await client.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    redirectTo: redirectTo,
                    queryParams: {
                        access_type: 'offline',
                        prompt: 'consent'
                    }
                }
            });

            if (error) throw error;
            return data;
        },

        /**
         * Send Password Reset Email.
         */
        async resetPasswordForEmail(email) {
            const client = getSupabase();
            if (!client) throw new Error('Supabase client unavailable.');

            const cleanEmail = email.trim().toLowerCase();
            const redirectTo = window.location.origin + '/forgot-password.html';
            const { data, error } = await client.auth.resetPasswordForEmail(cleanEmail, {
                redirectTo: redirectTo
            });

            if (error) throw error;
            return data;
        },

        /**
         * Update password for an authenticated session (e.g. from password reset link).
         */
        async updatePassword(newPassword) {
            const client = getSupabase();
            if (!client) throw new Error('Supabase client unavailable.');

            const { data, error } = await client.auth.updateUser({
                password: newPassword
            });

            if (error) throw error;
            return data;
        },

        /**
         * Log out the current user and redirect to login.
         */
        async signOut(redirectTo = 'login.html') {
            const client = getSupabase();
            setCachedUser(null);
            try {
                if (client) await client.auth.signOut();
            } catch (err) {
                console.warn('SignOut error:', err);
            } finally {
                // Clear any stored Supabase tokens
                for (let i = localStorage.length - 1; i >= 0; i--) {
                    const key = localStorage.key(i);
                    if (key && key.startsWith('sb-')) {
                        localStorage.removeItem(key);
                    }
                }
                localStorage.removeItem('powerforecast_user');
                if (redirectTo) {
                    window.location.href = redirectTo;
                }
            }
        },

        /**
         * Guard for protected pages (e.g. home.html).
         * If unauthenticated, immediately redirects to login.html.
         */
        async requireAuth(redirectTo = 'login.html') {
            const session = await this.getSession();
            if (!session || !session.user) {
                const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
                window.location.href = `${redirectTo}?redirect=${returnUrl}`;
                return false;
            }
            return true;
        },

        /**
         * Guard for auth pages (e.g. login.html, signup.html).
         * If already authenticated, immediately redirects to targetUrl (home.html).
         */
        async redirectIfAuthenticated(targetUrl = 'home.html') {
            const session = await this.getSession();
            if (session && session.user) {
                const params = new URLSearchParams(window.location.search);
                const redirect = params.get('redirect') || targetUrl;
                window.location.href = redirect;
                return true;
            }
            return false;
        }
    };

    window.PowerForecastAuth = PowerForecastAuth;

})(window);
