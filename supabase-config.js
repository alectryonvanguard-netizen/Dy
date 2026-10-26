
const SUPABASE_URL = "https://sdtaejcpxgqigqmdbzwg.supabase.co";

// Replace this with your Supabase publishable key.
const SUPABASE_PUBLISHABLE_KEY = "PASTE_YOUR_PUBLISHABLE_KEY_HERE";

const supabaseClient = window.supabase.createClient(
  SUPABASE_URL,
  SUPABASE_PUBLISHABLE_KEY
);
