import React from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import CodeBlock from '@theme/CodeBlock';
import Link from '@docusaurus/Link';

import '../css/custom.css';

const heroCode = `from django.db import models
from headless import expose


@expose()
class Article(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    published = models.BooleanField(default=False)`;

const routes = [
  { method: 'GET', path: '/api/blog.article', note: 'list' },
  { method: 'POST', path: '/api/blog.article', note: 'create' },
  { method: 'GET', path: '/api/blog.article/1', note: 'retrieve' },
  { method: 'PUT', path: '/api/blog.article/1', note: 'update' },
  { method: 'DELETE', path: '/api/blog.article/1', note: 'delete' },
];

const features = [
  {
    title: 'Routes per model',
    text: 'Decorate a model with @expose() and it gets list, detail, create, update and delete routes. You write no serializers, viewsets or URL patterns.',
  },
  {
    title: 'Fits your project',
    text: 'Works next to your existing apps, the Django admin and your Django REST Framework settings. Only the models you expose are in the API.',
  },
  {
    title: 'Singletons',
    text: 'Site settings and other one-off objects get a single GET and PUT route, created on the first write.',
  },
  {
    title: 'Filtering',
    text: 'Every lookup a field supports, from the query string: ?title__icontains=django. Exclude matches with ~.',
  },
  {
    title: 'Expandable relations',
    text: 'Include related exposed models inline with ?expand=, and serialize model properties as read-only fields.',
  },
  {
    title: 'Protected by default',
    text: 'Generated routes require authentication until you open them up. Secret key authentication and read-only models are included.',
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
              Django Headless generates a REST API for your Django models. Decorate a model with{' '}
              <code>@expose()</code> and your Next.js, Astro or static site frontend can read it from
              predictable routes.
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
