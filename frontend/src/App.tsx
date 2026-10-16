import { AssistantSection } from './sections/AssistantSection';
import { ContactSection } from './sections/ContactSection';
import { FeaturedWorkSection } from './sections/FeaturedWorkSection';
import { Footer } from './sections/Footer';
import { HeroSection } from './sections/HeroSection';
import { MetricsSection } from './sections/MetricsSection';
import { resumeUrl } from './data/profile';

export default function App() {
  return (
    <>
      <a className="skip-link" href="#home">
        Skip to main content
      </a>

      <nav className="anchor-nav" aria-label="Section navigation">
        <div className="container anchor-nav__inner">
          <a href="#work">Work</a>
          <a href="#assistant">Ask My AI</a>
          <a href="#contact">Contact</a>
          <a href={resumeUrl} target="_blank" rel="noopener noreferrer">
            Resume
            <span className="visually-hidden"> (opens in a new tab)</span>
          </a>
        </div>
      </nav>

      <main>
        <HeroSection />
        <MetricsSection />
        <FeaturedWorkSection />
        <AssistantSection />
        <ContactSection />
      </main>

      <Footer />
    </>
  );
}
