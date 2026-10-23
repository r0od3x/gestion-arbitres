/** Dictionnaire français (langue par défaut). Aucune chaîne en dur dans les composants. */
export const fr = {
  'app.title': 'Gestion des Arbitres',

  'nav.dashboard': 'Tableau de bord',
  'nav.referees': 'Arbitres',
  'nav.tournaments': 'Tournois',
  'nav.convocations': 'Mes convocations',
  'nav.profile': 'Mon profil',
  'nav.logout': 'Se déconnecter',

  'login.title': 'Connexion',
  'login.subtitle': 'Accédez à votre espace arbitre ou administrateur.',
  'login.email': 'Adresse e-mail',
  'login.password': 'Mot de passe',
  'login.submit': 'Se connecter',
  'login.pending': 'Connexion…',
  'login.error.credentials': 'E-mail ou mot de passe incorrect.',
  'login.error.generic': 'Connexion impossible. Réessayez dans un instant.',
  'login.error.emailRequired': 'Saisissez votre adresse e-mail.',
  'login.error.emailInvalid': 'Adresse e-mail invalide.',
  'login.error.passwordRequired': 'Saisissez votre mot de passe.',

  'referees.title': 'Arbitres',
  'referees.empty': 'Aucun arbitre pour le moment.',
  'referees.invite': 'Inviter un arbitre',
  'referees.search': 'Rechercher un arbitre…',

  'tournaments.title': 'Tournois',
  'tournaments.empty': 'Aucun tournoi pour le moment.',
  'tournaments.create': 'Créer un tournoi',

  'convocations.title': 'Mes convocations',
  'convocations.empty': "Vous n'avez aucune convocation.",
  'convocations.confirm': 'Je confirme',
  'convocations.decline': 'Je ne peux pas',

  'profile.title': 'Mon profil',
  'profile.whatsappOptIn': "J'accepte de recevoir mes convocations par WhatsApp",

  'grade.regional': 'Régional',
  'grade.national': 'National',
  'grade.continental': 'Continental',
  'grade.international': 'International',

  'status.draft': 'Brouillon',
  'status.published': 'Publié',
  'status.cancelled': 'Annulé',
  'status.completed': 'Terminé',
  'status.pending': 'En attente',
  'status.confirmed': 'Confirmé',
  'status.declined': 'Décliné',

  'common.loading': 'Chargement…',
  'common.retry': 'Réessayer',
  'common.cancel': 'Annuler',
  'common.save': 'Enregistrer',
  'common.error': 'Une erreur est survenue.',
  'common.notFound': 'Page introuvable.',
  'common.backHome': "Retour à l'accueil",
} as const

export type TranslationKey = keyof typeof fr
