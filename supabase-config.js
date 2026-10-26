
const SUPABASE_URL = "https://sdtaejcpxgqigqmdbzwg.supabase.co";

// Replace this with your Supabase publishable key.
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_GgrE1stQeNcA21QGqii_VQ_JNVAExWM";

const supabaseClient = window.supabase.createClient(
  SUPABASE_URL,
  SUPABASE_PUBLISHABLE_KEY
);
