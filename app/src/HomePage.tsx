import { IS_DEMO_DATA } from "./data";
import { pageHref } from "./route";
import { t, useLocale } from "./strings";
import { HOME_LINKS, TEAM_MEMBERS } from "./teamConfig";

export function HomePage({ regionId }: { regionId: string }) {
  const locale = useLocale();
  const isAr = locale === "ar";

  return (
    <article className="home-page" aria-labelledby="home-h">
      {IS_DEMO_DATA && <p className="notice">{t("methods.demo")}</p>}

      {/* Hero Section */}
      <section className="home-hero">
        <div className="home-hero-copy">
          <p className="home-kicker">{t("home.kicker")}</p>
          <h2 id="home-h">{t("home.title")}</h2>
          <p className="home-lead">{t("home.subtitle")}</p>
          <p className="fixed-line">{t("fixed.judgment")}</p>
          <div className="home-cta-row">
            <a className="home-btn home-btn--primary" href={pageHref(regionId, "map")}>
              {t("home.cta.map")} →
            </a>
            <a className="home-btn home-btn--secondary" href={pageHref(regionId, "scoreboard")}>
              {t("nav.scoreboard")}
            </a>
            <a className="home-btn home-btn--secondary" href={pageHref(regionId, "methods")}>
              {t("home.cta.methods")}
            </a>
          </div>
        </div>
        <div className="home-hero-visual" aria-label={t("home.heroCard.aria")}>
          <div className="home-witness-pills">
            <div className="home-witness-card">
              <span className="home-witness-badge">1</span>
              <div>
                <strong>{t("home.w1.title")}</strong>
                <p>{t("home.w1.desc")}</p>
              </div>
            </div>
            <div className="home-witness-card">
              <span className="home-witness-badge">2</span>
              <div>
                <strong>{t("home.w2.title")}</strong>
                <p>{t("home.w2.desc")}</p>
              </div>
            </div>
            <div className="home-witness-card">
              <span className="home-witness-badge">3</span>
              <div>
                <strong>{t("home.w3.title")}</strong>
                <p>{t("home.w3.desc")}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Impact Metrics Strip */}
      <section className="home-section" aria-labelledby="home-impact-h">
        <div className="home-section-head">
          <h3 id="home-impact-h">{t("home.impact.heading")}</h3>
          <p className="muted">{t("home.impact.subtitle")}</p>
        </div>
        <div className="home-impact-grid">
          <article className="home-stat-card">
            <strong className="home-stat-value">{t("home.impact.fields.val")}</strong>
            <span className="home-stat-label">{t("home.impact.fields.label")}</span>
            <p className="home-stat-note">{t("home.impact.fields.note")}</p>
          </article>
          <article className="home-stat-card">
            <strong className="home-stat-value">{t("home.impact.water.val")}</strong>
            <span className="home-stat-label">{t("home.impact.water.label")}</span>
            <p className="home-stat-note">{t("home.impact.water.note")}</p>
          </article>
          <article className="home-stat-card">
            <strong className="home-stat-value">{t("home.impact.cutoff.val")}</strong>
            <span className="home-stat-label">{t("home.impact.cutoff.label")}</span>
            <p className="home-stat-note">{t("home.impact.cutoff.note")}</p>
          </article>
          <article className="home-stat-card">
            <strong className="home-stat-value">{t("home.impact.parity.val")}</strong>
            <span className="home-stat-label">{t("home.impact.parity.label")}</span>
            <p className="home-stat-note">{t("home.impact.parity.note")}</p>
          </article>
        </div>
      </section>

      {/* Walkthrough Video + Paper & Repository Row */}
      <section className="home-two-col" aria-labelledby="home-media-h">
        <div className="home-card home-video-card">
          <div className="home-card-head">
            <h3 id="home-media-h">{t("home.video.heading")}</h3>
            <span className="home-pill">{t("home.video.badge")}</span>
          </div>
          {HOME_LINKS.demoVideoUrl ? (
            <div className="home-video-embed">
              <iframe
                src={HOME_LINKS.demoVideoUrl}
                title={t("home.video.heading")}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          ) : (
            <div className="home-video-placeholder">
              <div className="home-video-play-icon" aria-hidden="true">
                ▶
              </div>
              <p className="home-video-placeholder-title">{t("home.video.placeholderTitle")}</p>
              <p className="home-video-placeholder-desc">{t("home.video.placeholderDesc")}</p>
              <ul className="home-video-chapters">
                <li>{t("home.video.ch1")}</li>
                <li>{t("home.video.ch2")}</li>
                <li>{t("home.video.ch3")}</li>
                <li>{t("home.video.ch4")}</li>
              </ul>
            </div>
          )}
        </div>

        <div className="home-stack">
          {/* Revised Research Paper Card */}
          <article className="home-card" aria-labelledby="home-paper-h">
            <div className="home-card-head">
              <h3 id="home-paper-h">{t("home.paper.heading")}</h3>
              <span className="home-pill">{t("home.paper.badge")}</span>
            </div>
            <p>{t("home.paper.desc")}</p>
            <div className="home-btn-group">
              <a
                className="home-btn home-btn--primary"
                href={HOME_LINKS.paperPdfUrl}
                target="_blank"
                rel="noreferrer"
              >
                {t("home.paper.readPdf")}
              </a>
              <a className="home-btn home-btn--secondary" href={HOME_LINKS.paperDocxUrl} download>
                {t("home.paper.downloadDocx")}
              </a>
            </div>
          </article>

          {/* Public Repository Card */}
          <article className="home-card" aria-labelledby="home-repo-h">
            <div className="home-card-head">
              <h3 id="home-repo-h">{t("home.repo.heading")}</h3>
              <span className="home-pill">{t("home.repo.badge")}</span>
            </div>
            <p>{t("home.repo.desc")}</p>
            <div className="home-btn-group">
              <a
                className="home-btn home-btn--primary"
                href={HOME_LINKS.repoUrl}
                target="_blank"
                rel="noreferrer"
              >
                {t("home.repo.open")} ↗
              </a>
              <a className="home-btn home-btn--secondary" href={pageHref(regionId, "resources")}>
                {t("nav.resources")}
              </a>
              <a className="home-btn home-btn--secondary" href={pageHref(regionId, "terms")}>
                {t("nav.terms")}
              </a>
            </div>
          </article>
        </div>
      </section>

      {/* Team Members & Photos */}
      <section className="home-section" aria-labelledby="home-team-h">
        <div className="home-section-head">
          <h3 id="home-team-h">{t("home.team.heading")}</h3>
          <p className="muted">{t("home.team.subtitle")}</p>
        </div>
        <div className="home-team-grid">
          {TEAM_MEMBERS.map((member) => {
            const name = isAr ? member.nameAr : member.nameEn;
            const role = isAr ? member.roleAr : member.roleEn;
            const affiliation = isAr ? member.affiliationAr : member.affiliationEn;
            return (
              <article key={member.id} className="home-team-card">
                <div className="home-team-avatar">
                  {member.photoUrl ? (
                    <img src={member.photoUrl} alt={name} loading="lazy" />
                  ) : (
                    <span className="home-team-initials" aria-hidden="true">
                      {member.initials}
                    </span>
                  )}
                </div>
                <div className="home-team-meta">
                  <h4>{name}</h4>
                  <p className="home-team-role">{role}</p>
                  <p className="home-team-affil">{affiliation}</p>
                  <a className="home-team-email" href={`mailto:${member.email}`}>
                    {member.email}
                  </a>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </article>
  );
}
