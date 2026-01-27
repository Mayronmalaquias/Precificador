import React, { useEffect, useMemo, useState } from "react";
import "../assets/css/expert.css";
import expertsData from "../assets/data/experts.json";

export default function ExpertsPages({
  mode = "hub", // pode continuar passando, mas agora o componente se vira pelo ?slug=
  slug = "",
  data = null,
  jsonUrl = "",
  expertPageBasePath = "/Experts",
}) {
  const [state, setState] = useState({
    loading: true,
    error: "",
    data: null,
  });

  // Aplica o background com marca d'água definido no seu CSS
  useEffect(() => {
    document.body.classList.add("expert-bg");
    return () => document.body.classList.remove("expert-bg");
  }, []);

  // Lê o slug da URL (?slug=...) para funcionar igual ao HTML antigo
  const slugFromUrl = useMemo(() => {
    try {
      return new URLSearchParams(window.location.search).get("slug") || "";
    } catch {
      return "";
    }
  }, []);

  const effectiveSlug = (slug || slugFromUrl || "").trim();
  const effectiveMode = mode === "expert" || !!effectiveSlug ? "expert" : "hub";

  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        if (data) {
          if (alive) setState({ loading: false, error: "", data });
          return;
        }

        if (jsonUrl) {
          const res = await fetch(jsonUrl, { cache: "no-store" });
          const j = await res.json();
          if (alive) setState({ loading: false, error: "", data: j });
          return;
        }

        // fallback: JSON importado no bundle
        if (alive) setState({ loading: false, error: "", data: expertsData });
      } catch (e) {
        if (alive)
          setState({ loading: false, error: "Erro ao carregar dados.", data: null });
      }
    }

    load();
    return () => {
      alive = false;
    };
  }, [data, jsonUrl]);

  if (state.loading)
    return <div className="container my-4 text-center">Carregando...</div>;

  if (state.error)
    return <div className="container my-4 text-center">{state.error}</div>;

  const dataset = state.data || { citiesOrder: [], experts: [] };

  return effectiveMode === "expert" ? (
    <ExpertView slug={effectiveSlug} dataset={dataset} />
  ) : (
    <HubView dataset={dataset} expertPageBasePath={expertPageBasePath} />
  );
}

/* --- Helpers --- */
const ensureArray = (v) => (Array.isArray(v) ? v : []);
const normalizePhoneBR = (phone) => String(phone ?? "").replace(/\D+/g, "");

/* --- HUB VIEW (Lista de experts por cidade) --- */
function HubView({ dataset, expertPageBasePath }) {
  const citiesOrder = ensureArray(dataset.citiesOrder);
  const experts = ensureArray(dataset.experts);

  const { finalCities, byCity } = useMemo(() => {
    const map = new Map();
    citiesOrder.forEach((city) => map.set(city, []));

    experts.forEach((ex) => {
      ensureArray(ex.cities).forEach((city) => {
        if (!map.has(city)) map.set(city, []);
        map.get(city).push(ex);
      });
    });

    const extraCities = Array.from(map.keys())
      .filter((c) => !citiesOrder.includes(c))
      .sort();

    return { finalCities: [...citiesOrder, ...extraCities], byCity: map };
  }, [citiesOrder, experts]);

  return (
    <main className="expert-page">
      <div className="expert-container my-4">
        <div className="row mb-3">
          <div className="col-12">
            <h1 className="expert-title">Experts por Região</h1>
            <p className="expert-subtitle">
              Escolha uma região e conheça nossos especialistas.
            </p>
          </div>
        </div>

        {finalCities.map((city) => (
          <div className="city-block" key={city}>
            <div className="city-block-inner">
              <div className="city-block-header">
                <h2 className="city-title">{city}</h2>
              </div>

              <div className="city-cards">
                {byCity.get(city).length > 0 ? (
                  byCity.get(city).map((ex) => (
                    <a
                      key={ex.slug}
                      className="expert-card"
                      href={`${expertPageBasePath}?slug=${encodeURIComponent(ex.slug)}`}
                    >
                      <div className="expert-card-photo">
                        <img src={ex.photo} alt={ex.name} />
                      </div>

                      <div className="expert-card-body">
                        <p className="expert-card-name">{ex.name}</p>

                        {/* Se quiser igual ao JSON, mostre o roleTag */}
                        {ex.roleTag ? (
                          <p className="expert-card-tag">{ex.roleTag}</p>
                        ) : (
                          <p className="expert-card-tag">Expert {city}</p>
                        )}
                      </div>
                    </a>
                  ))
                ) : (
                  <div className="empty-city">Em breve, novos experts nesta região.</div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}

/* --- EXPERT VIEW (Perfil detalhado) --- */
function ExpertView({ slug, dataset }) {
  const expert = useMemo(() => {
    const s = String(slug || "").toLowerCase().trim();
    return ensureArray(dataset.experts).find(
      (e) => String(e.slug || "").toLowerCase().trim() === s
    );
  }, [dataset.experts, slug]);

  if (!expert) {
    return (

      <div className="container my-4">
        Expert não encontrado. (slug: <b>{String(slug || "")}</b>)
      </div>
    );
  }

  const whatsappDigits = normalizePhoneBR(expert.contacts?.whatsapp);
  const waLink = `https://api.whatsapp.com/send?phone=${whatsappDigits}&text=${encodeURIComponent(
    `Olá, ${expert.name}! Vim pela página de Experts.`
  )}`;

  return (
    <main className="container-fluid expert-page expert-slug"> 
      <div className="container my-4">
        <section className="expert-profile-wrap">
          <div className="expert-profile-grid">
            <div className="expert-hero-photo">
              <img src={expert.photo} alt={expert.name} />
            </div>

            <div>
              <h1 className="expert-name">{expert.name}</h1>

              <div className="expert-cities">
                {ensureArray(expert.cities).join(" • ")}
                {expert.roleTag ? ` • ${expert.roleTag}` : ""}
              </div>

              {expert.bioShort ? (
                <p className="expert-bio-short">{expert.bioShort}</p>
              ) : null}

              <div className="expert-bio-full-wrap">
                {String(expert.bioFull || "")
                  .split(/\n\s*\n/g)
                  .filter(Boolean)
                  .map((p, i) => (
                    <p key={i} className="expert-bio-full">
                      {p}
                    </p>
                  ))}
              </div>

              <div className="expert-cta">
                <div className="expert-cta-box">
                  {whatsappDigits ? (
                    <a
                      className="btn btn-soft-primary"
                      target="_blank"
                      rel="noopener"
                      href={waLink}
                    >
                      Falar no WhatsApp
                    </a>
                  ) : null}

                  <a className="btn btn-soft" href="#expert-properties">
                    Ver imóveis
                  </a>

                  {expert.contacts?.instagram ? (
                    <a
                      className="btn btn-soft"
                      target="_blank"
                      rel="noopener"
                      href={expert.contacts.instagram}
                    >
                      Instagram
                    </a>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="row mt-5" id="expert-properties">
          <div className="col-12">
            <h2 className="expert-section-title">Imóveis deste expert</h2>
          </div>

          {ensureArray(expert.properties).length > 0 ? (
            ensureArray(expert.properties).map((p, i) => (
              <div className="col-12 col-md-6 col-lg-4 mt-3" key={i}>
                <a className="property-card" href={p.url} target="_blank" rel="noopener">
                  <div className="property-thumb">
                    <img src={p.thumb} alt={p.title} />
                  </div>
                  <div className="property-body">
                    <p className="property-title">{p.title}</p>
                    <div className="property-cta">Ver anúncio</div>
                  </div>
                </a>
              </div>
            ))
          ) : (
            <div className="col-12 mt-3">
              <div className="empty-city">Sem imóveis cadastrados para este expert.</div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
