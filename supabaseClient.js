/**
 * PowerForecast — Supabase Client Initializer
 * Exports the official Supabase client instance using environment / global settings.
 */

(function (window) {
    'use strict';

    const SUPABASE_URL = window.SUPABASE_URL || 'https://ysfruhloqnelyysdwvog.supabase.co';
    const SUPABASE_ANON_KEY = window.SUPABASE_ANON_KEY || 'sb_publishable_GjVlGJjSHfWubSBswskS1A_gqTK6e_6';

    let _supabase = null;

    function initSupabase() {
        if (_supabase) return _supabase;

        if (window.supabase && typeof window.supabase.createClient === 'function') {
            _supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
                auth: {
                    persistSession: true,
                    autoRefreshToken: true,
                    detectSessionInUrl: true,
                    storage: window.localStorage
                }
            });
            return _supabase;
        }

        console.error('Supabase JS library (@supabase/supabase-js) is not loaded.');
        return null;
    }

    window.supabaseClient = initSupabase();
    window.getSupabaseClient = initSupabase;

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { SUPABASE_URL, SUPABASE_ANON_KEY, initSupabase };
    }
})(window);
