# VueloDigno Next.js Prototype 🚀

An Apple iPhone 15 Pro-inspired landing page for VueloDigno - Mexican flight compensation legal-tech.

## Features ✨

- **Dark Mode Obsidian Design** - Premium dark theme with gradient mesh backgrounds
- **Liquid Glass Effects** - Frosted glass cards with blur effects
- **3D Floating Claim Card** - Scales and rotates as you scroll with typing animation
- **Apple-style Bento Grid** - Explains Article 47 Bis passenger rights
- **Smooth Scroll Animations** - Framer Motion powered transitions
- **Scrollytelling Flow** - Text fades in/out as you scroll through sections
- **API Routes** - Backend logic ported from Flask to Next.js

## Tech Stack 🛠

- **Next.js 14** - React framework with App Router
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Animation library
- **TypeScript** - Type safety
- **Resend** - Email delivery service

## Prerequisites 📋

Before running, make sure you have:
- **Node.js 18+** installed ([download here](https://nodejs.org/))
- **npm** or **yarn** or **pnpm**

## Quick Start 🚀

1. **Navigate to the project**:
   ```bash
   cd /Users/zelma/Desktop/ZelmaHelps_Agent/vuelodigno-next
   ```

2. **Install dependencies**:
   ```bash
   npm install
   # or
   yarn install
   # or
   pnpm install
   ```

3. **Run the development server**:
   ```bash
   npm run dev
   # or
   yarn dev
   # or
   pnpm dev
   ```

4. **Open in browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Project Structure 📁

```
vuelodigno-next/
├── app/
│   ├── globals.css      # Global styles, glass effects, animations
│   ├── layout.tsx       # Root layout with metadata
│   └── page.tsx         # Main landing page
├── components/
│   ├── HeroSection.tsx  # Hero with massive typography
│   ├── ClaimCard.tsx    # 3D animated claim card with typing
│   ├── BentoGrid.tsx    # Apple-style grid for law info
│   └── ScrollIndicator.tsx
├── tailwind.config.ts   # Custom colors, animations
├── package.json
└── README.md
```

## Design Highlights 🎨

### Colors
- **Obsidian Background**: `#0a0a0a` - Deep black
- **Gold Accent**: `#f59e0b` - Compensation highlights
- **Blue Accent**: `#3b82f6` - CTA buttons

### Effects
- **Glass Effect**: `backdrop-filter: blur(20px)` with subtle borders
- **Glow**: Box shadows with colored opacity
- **Gradient Text**: Gold gradient for key numbers

## Customization 🔧

### Change the compensation example:
Edit `/components/ClaimCard.tsx` - update the TypewriterText values

### Modify law sections:
Edit `/components/BentoGrid.tsx` - update BentoItem props

### Adjust animations:
Framer Motion props like `initial`, `animate`, `transition` control all animations

## What's Next? 🤔

If you like this direction, the next steps would be:

1. **Add the actual form** - Multi-step calculator
2. **Connect to Flask backend** - API routes for email generation
3. **Add success page** - Animated confirmation
4. **Deploy** - Vercel or similar

## Screenshots 📸

[Run the dev server to see it in action!]

---

Made with ❤️ for VueloDigno
