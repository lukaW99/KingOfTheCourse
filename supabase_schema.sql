-- King of the Course — Supabase schema
-- Run this in the Supabase SQL Editor (Project > SQL Editor > New Query)

create extension if not exists "uuid-ossp";

-- Players
create table if not exists players (
    id uuid primary key default uuid_generate_v4(),
    name text not null unique,
    photo_url text,
    created_at timestamptz default now()
);

-- Rounds
create table if not exists rounds (
    id uuid primary key default uuid_generate_v4(),
    player_id uuid references players(id) on delete cascade,
    round_date date not null,
    course text not null,
    handicap numeric not null,
    points integer not null,
    ladies_tee_count integer default 0,
    four_putt_count integer default 0,
    off_green_count integer default 0,
    bunker_count integer default 0,
    created_at timestamptz default now()
);

-- Manual / monthly fines (e.g. "didn't play this month")
create table if not exists monthly_fines (
    id uuid primary key default uuid_generate_v4(),
    player_id uuid references players(id) on delete cascade,
    month_label text,
    amount numeric not null,
    reason text,
    created_at timestamptz default now()
);

-- Gallery photos (fun, non-scoring)
create table if not exists gallery_photos (
    id uuid primary key default uuid_generate_v4(),
    url text not null,
    caption text,
    created_at timestamptz default now()
);

-- Row Level Security: open read/write since the app has no login system
-- (the URL itself is the access control, per your setup).
alter table players enable row level security;
alter table rounds enable row level security;
alter table monthly_fines enable row level security;
alter table gallery_photos enable row level security;

create policy "Public full access - players" on players
    for all using (true) with check (true);

create policy "Public full access - rounds" on rounds
    for all using (true) with check (true);

create policy "Public full access - monthly_fines" on monthly_fines
    for all using (true) with check (true);

create policy "Public full access - gallery_photos" on gallery_photos
    for all using (true) with check (true);
