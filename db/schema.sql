\restrict dbmate

-- Dumped from database version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: digest_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.digest_items (
    id bigint NOT NULL,
    digest_id bigint NOT NULL,
    item_id bigint NOT NULL,
    tier text NOT NULL,
    "position" integer NOT NULL,
    synthesis text,
    CONSTRAINT digest_items_tier_check CHECK ((tier = ANY (ARRAY['practice_changing'::text, 'worth_knowing'::text, 'fyi'::text])))
);


--
-- Name: digest_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.digest_items_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: digest_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.digest_items_id_seq OWNED BY public.digest_items.id;


--
-- Name: digests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.digests (
    id bigint NOT NULL,
    sent_at timestamp with time zone,
    is_dry_run boolean DEFAULT false NOT NULL,
    week_in_brief text,
    screened_count integer,
    surfaced_count integer,
    html text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: digests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.digests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: digests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.digests_id_seq OWNED BY public.digests.id;


--
-- Name: eval_labels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eval_labels (
    id bigint NOT NULL,
    pmid text,
    doi text,
    title text NOT NULL,
    journal text,
    publication_date date,
    true_tier text NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT eval_labels_true_tier_check CHECK ((true_tier = ANY (ARRAY['practice_changing'::text, 'worth_knowing'::text, 'fyi'::text, 'noise'::text])))
);


--
-- Name: eval_labels_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eval_labels_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eval_labels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eval_labels_id_seq OWNED BY public.eval_labels.id;


--
-- Name: feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.feedback (
    id bigint NOT NULL,
    item_id bigint NOT NULL,
    digest_id bigint,
    verdict text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT feedback_verdict_check CHECK ((verdict = ANY (ARRAY['useful'::text, 'not_relevant'::text, 'knew_it'::text, 'deep_dive'::text])))
);


--
-- Name: feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.feedback_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.feedback_id_seq OWNED BY public.feedback.id;


--
-- Name: items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.items (
    id bigint NOT NULL,
    source_id bigint NOT NULL,
    external_id text NOT NULL,
    doi text,
    pmid text,
    title text NOT NULL,
    journal text,
    item_type text,
    study_design text,
    sample_size integer,
    published_on date,
    abstract text,
    url text NOT NULL,
    oa_url text,
    oa_source text,
    prefilter text DEFAULT 'pending'::text NOT NULL,
    raw jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT items_oa_source_check CHECK ((oa_source = ANY (ARRAY['unpaywall'::text, 'pmc'::text])))
);


--
-- Name: items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.items_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.items_id_seq OWNED BY public.items.id;


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL
);


--
-- Name: scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scores (
    id bigint NOT NULL,
    item_id bigint NOT NULL,
    relevance_tier text NOT NULL,
    evidence_level text,
    one_line_takeaway text,
    reasoning text,
    topics text[] DEFAULT '{}'::text[] NOT NULL,
    confidence numeric(3,2),
    model text NOT NULL,
    prompt_version text NOT NULL,
    profile_version text NOT NULL,
    is_current boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT scores_relevance_tier_check CHECK ((relevance_tier = ANY (ARRAY['practice_changing'::text, 'worth_knowing'::text, 'fyi'::text, 'noise'::text])))
);


--
-- Name: scores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scores_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scores_id_seq OWNED BY public.scores.id;


--
-- Name: sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sources (
    id bigint NOT NULL,
    kind text NOT NULL,
    name text NOT NULL,
    last_success_at timestamp with time zone,
    last_error text,
    last_error_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT sources_kind_check CHECK ((kind = ANY (ARRAY['pubmed'::text, 'fda'::text, 'society_feed'::text])))
);


--
-- Name: sources_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sources_id_seq OWNED BY public.sources.id;


--
-- Name: digest_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.digest_items ALTER COLUMN id SET DEFAULT nextval('public.digest_items_id_seq'::regclass);


--
-- Name: digests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.digests ALTER COLUMN id SET DEFAULT nextval('public.digests_id_seq'::regclass);


--
-- Name: eval_labels id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_labels ALTER COLUMN id SET DEFAULT nextval('public.eval_labels_id_seq'::regclass);


--
-- Name: feedback id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback ALTER COLUMN id SET DEFAULT nextval('public.feedback_id_seq'::regclass);


--
-- Name: items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items ALTER COLUMN id SET DEFAULT nextval('public.items_id_seq'::regclass);


--
-- Name: scores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores ALTER COLUMN id SET DEFAULT nextval('public.scores_id_seq'::regclass);


--
-- Name: sources id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources ALTER COLUMN id SET DEFAULT nextval('public.sources_id_seq'::regclass);


--
-- Name: digest_items digest_items_digest_id_item_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.digest_items
    ADD CONSTRAINT digest_items_digest_id_item_id_key UNIQUE (digest_id, item_id);


--
-- Name: digest_items digest_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.digest_items
    ADD CONSTRAINT digest_items_pkey PRIMARY KEY (id);


--
-- Name: digests digests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.digests
    ADD CONSTRAINT digests_pkey PRIMARY KEY (id);


--
-- Name: eval_labels eval_labels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_labels
    ADD CONSTRAINT eval_labels_pkey PRIMARY KEY (id);


--
-- Name: feedback feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (id);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


--
-- Name: items items_source_id_external_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_source_id_external_id_key UNIQUE (source_id, external_id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: scores scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_pkey PRIMARY KEY (id);


--
-- Name: sources sources_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_name_key UNIQUE (name);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (id);


--
-- Name: digest_items_digest_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX digest_items_digest_id_idx ON public.digest_items USING btree (digest_id);


--
-- Name: feedback_item_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX feedback_item_id_idx ON public.feedback USING btree (item_id);


--
-- Name: items_prefilter_passed_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX items_prefilter_passed_idx ON public.items USING btree (published_on) WHERE (prefilter = 'passed'::text);


--
-- Name: scores_item_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_item_id_idx ON public.scores USING btree (item_id);


--
-- Name: scores_one_current_per_item; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX scores_one_current_per_item ON public.scores USING btree (item_id) WHERE is_current;


--
-- Name: digest_items digest_items_digest_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.digest_items
    ADD CONSTRAINT digest_items_digest_id_fkey FOREIGN KEY (digest_id) REFERENCES public.digests(id);


--
-- Name: digest_items digest_items_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.digest_items
    ADD CONSTRAINT digest_items_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id);


--
-- Name: feedback feedback_digest_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_digest_id_fkey FOREIGN KEY (digest_id) REFERENCES public.digests(id);


--
-- Name: feedback feedback_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id);


--
-- Name: items items_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id);


--
-- Name: scores scores_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id);


--
-- PostgreSQL database dump complete
--

\unrestrict dbmate


--
-- Dbmate schema migrations
--

INSERT INTO public.schema_migrations (version) VALUES
    ('20260711120001'),
    ('20260711120002'),
    ('20260711120003'),
    ('20260711120004'),
    ('20260711120005'),
    ('20260711120006'),
    ('20260711120007');
