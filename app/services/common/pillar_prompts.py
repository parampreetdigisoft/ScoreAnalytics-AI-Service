"""
Data Analyzer Service - LLM-powered analysis of SQL Server data
Enhanced with Veridian Urban Index pillar-specific prompts
"""

class PillarPrompts:
    """Veridian Urban Index pillar-specific prompt templates"""
    
    @staticmethod
    def get_pillar_context(pillarId: int) -> str:
        """Get specific context and evaluation criteria for each pillar"""
        
        contexts = {
             # Urban Governance and Integrity
            13: """
                Focus: Transparency, participation, accountability, ethics, institutional capacity
                Key Evidence: Municipal budgets, procurement records, audit reports, ombudsman data,
                anti-corruption statistics, FOI response rates, council minutes
                Red Flags: Missing oversight data, zero complaints, perfect integrity claims
                Trustworthy Sources: City auditor reports, Transparency International, World Justice Project
            """,
            # Urban Education, Learning Ecosystems, and Knowledge Equity
            14: """
                Focus: Access, quality, spatial equity, digital readiness, lifelong learning
                Key Evidence: Enrollment rates, completion rates, teacher-student ratios, school mapping,
                budget allocations, inspection reports, early childhood to university coverage
                Red Flags: National-only data, dual systems (public vs private gaps), spatial inequality
                Trustworthy Sources: UNESCO Institute for Statistics, UNICEF, city education bureaus
            """,

            # Business and Investment Environment
            11: """
                Focus: Ease of doing business, property rights, dispute resolution, capital access
                Key Evidence: Business registration data, licensing portals, commercial court performance,
                land registries, investment promotion, tax structure, SME treatment
                Red Flags: Informal market contradictions, hostile regulation, weak property enforcement
                Trustworthy Sources: World Bank Enterprise Surveys, business registration agencies
            """,
            
            #Smartness and Digital Readiness
            2: """
                Focus: Digital infrastructure, e-governance, data systems, digital inclusion, cybersecurity
                Key Evidence: Broadband penetration, e-service adoption, data protection enforcement,
                cybersecurity incidents, public Wi-Fi, school connectivity, usage gaps by gender/income
                Red Flags: Smart city branding without metrics, digital inequality, vendor marketing
                Trustworthy Sources: ITU, national telecom regulators, municipal ICT offices
            """,
            
            #Cleanliness and Sanitation
            1: """
                Focus: Solid waste, liquid waste, hygiene, public cleanliness, sanitation governance
                Key Evidence: Waste collection coverage, sewerage networks, treatment plants, recycling rates,
                WASH-related disease incidence, school/market WASH audits, budget allocations
                Red Flags: CBD cleanliness vs informal settlements, missing treatment data, coverage gaps
                Trustworthy Sources: WHO/UNICEF JMP, UN-Habitat, municipal sanitation authorities
            """,
            
            #Conflict Risk and Early Warning
            3: """
                Focus: Structural drivers, protest dynamics, hate speech, early warning, mediation
                Key Evidence: Police statistics, protest/clash data, grievance logs, land disputes,
                eviction records, peace committee reports, media restrictions
                Red Flags: "No incidents" in tense environments, under-reporting, service-delivery protests
                Trustworthy Sources: ACLED, UNDP fragility diagnostics, police records
            """,
            
            #Civic Resilience and Social Cohesion
            10: """
                Focus: Trust, solidarity systems, civic participation, inclusion, community resilience
                Key Evidence: Election turnout, participatory budgeting, neighborhood associations,
                volunteer networks, trust surveys, interpersonal solidarity indicators
                Red Flags: High trust in brittle contexts, absent civil society in authoritarian settings
                Trustworthy Sources: Afrobarometer, Latinobarómetro, UNDP social cohesion assessments
            """,
            
            #Housing and Land Security
            7: """
                Focus: Tenure security, affordability, evictions, gendered land rights, spatial justice
                Key Evidence: Land registries, titling records, zoning maps, eviction data, public housing,
                informal settlement upgrading, inheritance laws, women's land rights
                Red Flags: Forced evictions, mass demolitions, gender-blind data, informal=illegitimate framing
                Trustworthy Sources: UN-Habitat, World Bank LGAF, cadastral records
            """,
            
            #Environmental Hazards and Urban Safety
            9: """
                Focus: Climate/disaster risk, hazard mapping, exposure, built environment, health risks
                Key Evidence: Hazard maps, disaster loss data, flood/heat records, air/water quality,
                building inspections, drainage plans, adaptation measures
                Red Flags: Hazard maps ignoring peripheries, no adaptation despite projections
                Trustworthy Sources: IPCC, UNDRR, EM-DAT, WHO environmental health data
            """,
            
            #Public Health, Inclusion, and Wellbeing
            8: """
                Focus: Healthcare access, mental health, disability inclusion, food security, social protection
                Key Evidence: Facility locations, staffing, service coverage, mortality data, insurance,
                emergency services, nutrition programs, disability registries, accessibility audits
                Red Flags: Averaged disparities, scarce mental health/disability data, informal settlement neglect
                Trustworthy Sources: WHO Global Health Observatory, UNICEF, health ministries
            """,
            
            #Infrastructure, Mobility, and Service Delivery
            4: """
                Focus: Water, electricity, transport, ICT, service reliability, equitable access, maintenance
                Key Evidence: Connection rates, outages, tariff structures, route maps, ridership, safety,
                maintenance budgets, road crashes, pedestrian safety, complaint systems
                Red Flags: Network presence ≠ usable access, low maintenance budgets, excluded informal transport
                Trustworthy Sources: UN-Habitat, utilities, transport authorities, World Bank
            """,
            #Green Infrastructure, Forests, and Urban Ecology
            5: """
                Focus: Urban forests, parks, biodiversity, nature-based solutions, ecological justice
                Key Evidence: Park locations/sizes, tree inventories, canopy cover, protected areas,
                biodiversity data, green corridors, climate strategies with NBS
                Red Flags: Unequal green access by income, unverified tree-planting, displacement via beautification
                Trustworthy Sources: UNEP, FAO, Global Forest Watch, parks departments
            """,
            
            #Employment and Workforce Development
            12: """
                Focus: Job creation, decent work, skills, labor rights, inclusion of marginalized workers
                Key Evidence: Labor force surveys, employment services, TVET programs, local content clauses,
                labor inspections, social security, unemployment benefits
                Red Flags: Underemployment ignored, megaprojects without skills programs, weak labor enforcement
                Trustworthy Sources: ILO, labor ministries, World Bank jobs diagnostics
            """,
            
            #Cultural Heritage, Identity, and Narrative Power
            6: """
                Focus: Heritage protection, inclusive memory, symbolic representation, creative economies
                Key Evidence: Protected sites, heritage registers, cultural budgets, naming decisions,
                monuments/memorials, arts funding, minority histories, language visibility
                Red Flags: Narrative erasure, revitalization displacing communities, missing minority representation
                Trustworthy Sources: UNESCO, ICOMOS, culture ministries, academic urban memory studies
            """
        }
        
        return contexts.get(pillarId, contexts[13]) 


