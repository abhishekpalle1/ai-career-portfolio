import { AssistantSection } from './sections/AssistantSection';
import { ExperienceSection } from './sections/ExperienceSection';
import { Footer } from './sections/Footer';
import { HeroSection } from './sections/HeroSection';

export default function App() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>

      <main id="main">
        <HeroSection />
        <ExperienceSection />
        <AssistantSection />
      </main>

      <Footer />
    </>
  );
}
