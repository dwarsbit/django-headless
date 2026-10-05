import React from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import CodeBlock from '@theme/CodeBlock';
import Link from '@docusaurus/Link';

import '../css/custom.css';

const heroCode = `from django.db import models
from headless import expose

@expose()
class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    published = models.BooleanField(default=False)`;

const routes = [
  { method: 'GET', path: '/api/blog.blogpost', note: 'list + filters' },
  { method: 'POST', path: '/api/blog.blogpost', note: 'create' },
  { method: 'GET', path: '/api/blog.blogpost/1', note: 'detail' },
  { method: 'PUT', path: '/api/blog.blogpost/1', note: 'update' },
  { method: 'DELETE', path: '/api/blog.blogpost/1', note: 'delete' },
];

const features = [
  {
    emoji: '🎯',
    title: 'One decorator, full API',
    text: 'Add @expose() to any model and get list, detail and CRUD endpoints — no serializers, viewsets or URL wiring to write.',
  },
  {
    emoji: '🤝',
    title: 'Plays nice with Django',
    text: 'Works alongside your existing apps, admin and DRF configuration. You decide what gets exposed.',
  },
  {
    emoji: '💈',
    title: 'Singletons',
    text: 'Site settings and configuration objects become a single GET/PUT resource, created on first write.',
  },
  {
    emoji: '🔍',
    title: 'ORM filtering',
    text: 'Every Django lookup per field, straight from the query string: ?title__icontains=django, exclusions with ~.',
  },
  {
    emoji: '🔗',
    title: 'Expandable relations',
    text: 'Optional flex-fields serialization expands related exposed models inline with ?expand=.',
  },
  {
    emoji: '🛡️',
    title: 'Secure by configuration',
    text: 'Built-in secret key authentication, permission overrides for generated routes, and read-only models.',
  },
];

export default function Home() {
  const { siteConfig } = useDocusaurusContext();

  return (
    <Layout title="Home" description={siteConfig.tagline}>
      <header className="hero-dhh">
        <div className="container">
          <div>
            <h1>
              Your Django models.
              <br />
              A REST API. No boilerplate.
            </h1>
            <p className="tagline">
              Django Headless turns Django into a headless CMS backend. Decorate a model with{' '}
              <code>@expose()</code> and a predictable, read-friendly REST API appears — ready for
              your Next.js, Astro or any JAMstack frontend.
            </p>
            <div className="buttons">
              <Link className="button button--lg button-dhh-primary" to="/docs/installation">
                Get started
              </Link>
              <Link
                className="button button--lg button-dhh-secondary"
                href="https://github.com/dwarsbit/django-headless"
              >
                GitHub
              </Link>
            </div>
          </div>
          <div className="hero-visual">
            <CodeBlock language="python">{heroCode}</CodeBlock>
            <div className="hero-routes">
              {routes.map((route) => (
                <div className="hero-route" key={`${route.method}-${route.path}`}>
                  <span className="method">{route.method}</span>
                  <span>{route.path}</span>
                  <span className="auto">{route.note}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </header>
      <main>
        <section className="features-dhh">
          <div className="container">
            <h2 className="section-title">Everything included, nothing required</h2>
            <div className="features-grid">
              {features.map((feature) => (
                <div className="feature-card" key={feature.title}>
                  <span className="emoji" aria-hidden="true">
                    {feature.emoji}
                  </span>
                  <h3>{feature.title}</h3>
                  <p>{feature.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
